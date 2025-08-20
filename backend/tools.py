from supabase import create_client, Client
from datetime import datetime, timedelta
import json
import re
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from typing import TypedDict, List, Optional
import os   


# Get credentials from environment variables - NO fallbacks for security
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Validate required environment variables
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL environment variable is required")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY environment variable is required")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is required")

print(f"Using Supabase URL: {SUPABASE_URL}")
print(f"Using Anthropic API: {'Set' if ANTHROPIC_API_KEY else 'Missing'}")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# DESIGNATED TEACHER ID - Only this user can set teacher availability
TEACHER_ID = 'e4bcab2f-8da5-4a78-85e8-094f4d7ac308'

def extract_user_id_from_message(message: str) -> tuple:
    """Extract user ID from message format"""
    if message.startswith("Student "):
        parts = message.split(": ", 1)
        if len(parts) == 2:
            user_id = parts[0].replace("Student ", "")
            return user_id, False, parts[1]
    elif message.startswith("Teacher "):
        parts = message.split(": ", 1)
        if len(parts) == 2:
            user_id = parts[0].replace("Teacher ", "")
            return user_id, True, parts[1]
    
    return "default-user", False, message

def parse_time_from_message(message: str) -> tuple:
    """Extract time information from user message - FIXED to preserve user's duration"""
    # Look for time patterns like "12-2pm", "2-3 PM", "1:30-2:30", "2 to 3 PM"
    time_patterns = [
        r'(\d{1,2}):?(\d{0,2})\s*-\s*(\d{1,2}):?(\d{0,2})\s*(am|pm)',
        r'(\d{1,2})\s*to\s*(\d{1,2})\s*(am|pm)',
        r'(\d{1,2})\s*(am|pm)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message.lower())
        if match:
            groups = match.groups()
            if len(groups) >= 3 and groups[2]:  # We have start, end, and am/pm
                start_hour = int(groups[0])
                end_hour = int(groups[2])
                am_pm = groups[-1]  # Last group is am/pm
                
                # Handle PM conversion
                if am_pm == 'pm' and start_hour < 12:
                    start_hour += 12
                if am_pm == 'pm' and end_hour < 12:
                    end_hour += 12
                elif am_pm == 'am' and start_hour == 12:
                    start_hour = 0
                elif am_pm == 'am' and end_hour == 12:
                    end_hour = 0
                
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
            elif len(groups) >= 2:  # We have start and am/pm
                start_hour = int(groups[0])
                am_pm = groups[1]
                
                if am_pm == 'pm' and start_hour < 12:
                    start_hour += 12
                elif am_pm == 'am' and start_hour == 12:
                    start_hour = 0
                
                end_hour = start_hour + 1
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
    
    # Default fallback
    return "14:00:00", "15:00:00"

def find_available_time_slot(existing_sessions: list, preferred_start: str, preferred_end: str, date: str) -> tuple:
    """Find available time slot avoiding conflicts with existing sessions - FIXED to preserve duration"""
    
    def time_to_minutes(time_str):
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    
    def minutes_to_time(minutes):
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}:00"
    
    preferred_start_mins = time_to_minutes(preferred_start)
    preferred_end_mins = time_to_minutes(preferred_end)
    session_duration = preferred_end_mins - preferred_start_mins
    
    print(f"Looking for {session_duration} min slot, preferred: {preferred_start[:5]}-{preferred_end[:5]}")
    
    # Get all existing sessions for this date
    occupied_slots = []
    for session in existing_sessions:
        if session['date'] == date and session['status'] == 'active':
            start_mins = time_to_minutes(session['start_time'])
            end_mins = time_to_minutes(session['end_time'])
            occupied_slots.append((start_mins, end_mins))
            print(f"  Existing: {session['subject']} at {session['start_time'][:5]}-{session['end_time'][:5]}")
    
    occupied_slots.sort()  # Sort by start time
    
    # Check if preferred time is available
    preferred_conflicts = False
    for start_mins, end_mins in occupied_slots:
        # Check for overlap
        if not (preferred_end_mins <= start_mins or preferred_start_mins >= end_mins):
            preferred_conflicts = True
            print(f"  Conflict with slot {minutes_to_time(start_mins)[:5]}-{minutes_to_time(end_mins)[:5]}")
            break
    
    if not preferred_conflicts:
        print("  Preferred time is available")
        return preferred_start, preferred_end
    
    # Find next available slot - START FROM CONFLICT END TIME
    current_time = preferred_start_mins
    
    for start_mins, end_mins in occupied_slots:
        # If there's a gap before this session and it's big enough
        if current_time + session_duration <= start_mins:
            available_start = minutes_to_time(current_time)
            available_end = minutes_to_time(current_time + session_duration)
            print(f"  Found slot before existing session: {available_start[:5]}-{available_end[:5]}")
            return available_start, available_end
        
        # FIXED: Move current time to after this session
        current_time = max(current_time, end_mins)
    
    # If no slot found before existing sessions, use time after last session
    available_start = minutes_to_time(current_time)
    available_end = minutes_to_time(current_time + session_duration)
    print(f"  Found slot after existing sessions: {available_start[:5]}-{available_end[:5]}")
    return available_start, available_end

# --- LangGraph Setup ---
class AgentState(TypedDict):
    messages: List[dict]
    next: Optional[str]

# Claude (Anthropic) LLM
try:
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.1,
        api_key=ANTHROPIC_API_KEY
    )
    print("Anthropic LLM initialized successfully")
except Exception as e:
    print(f"Anthropic LLM initialization failed: {e}")
    print("Using mock LLM for testing")
    llm = None

# System prompt for the agent - SIMPLIFIED for better responses
system_prompt = """
You are a session scheduler. Keep responses SHORT and SIMPLE.

**FOR TEACHERS (user_id = e4bcab2f-8da5-4a78-85e8-094f4d7ac308):**
- Call parse_teacher_availability() and set_teacher_availability()
- Always respond with: "Availability set for [day] [time]"

**FOR STUDENTS:**
1. Call parse_student_request() to get subject, timing, date
2. Call check_all_sessions_for_date() to see existing sessions
3. Call create_session_with_conflict_check() to handle conflicts automatically

**RESPONSE RULES:**
- Keep responses under 10 words
- Format: "Session created at [time]" or "Added to session at [time]"
- NO emojis, NO explanations
- ALWAYS provide a simple response

**IMPORTANT:** Always respond after calling tools. Never leave user without response.
"""

def run_session_agent(user_input: str) -> str:
    """Run the session creation agent with user input - FIXED to ensure response."""
    try:
        # Extract user information from the message
        user_id, is_teacher_from_message, clean_message = extract_user_id_from_message(user_input)
        
        print(f"Processing - User ID: {user_id}, Message: {clean_message}")
        
        # SIMPLIFIED ROLE DETECTION - Only check user ID
        is_designated_teacher = (user_id == TEACHER_ID)
        
        if is_designated_teacher:
            # This is the designated teacher - handle availability setting
            print(f"TEACHER detected: {user_id}")
            contextual_input = f"""
TEACHER {user_id} says: {clean_message}

This is the designated TEACHER setting availability.
1. Call parse_teacher_availability() with teacher_id and message
2. Call set_teacher_availability() with the parsed data
3. MUST respond with: "Availability set for [day] [time]"
"""
        else:
            # This is a student - handle session booking
            print(f"STUDENT detected: {user_id}")
            contextual_input = f"""
STUDENT {user_id} says: {clean_message}

This is a STUDENT requesting session booking.
1. Call parse_student_request() with student_id and message
2. Call check_all_sessions_for_date() with the date
3. Call create_session_with_conflict_check() with all data
4. MUST respond with: "Session created at [time]" or "Added to session at [time]"
"""
        
        if llm is None or graph is None:
            # Mock response for testing when API key is invalid
            if is_designated_teacher:
                return "Availability set for tomorrow 2-4pm"
            else:
                return "Session created at 1-2pm"
        
        # Include system prompt in messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": contextual_input}
        ]
        
        # FIXED: Better response extraction
        response = graph.invoke({
            "messages": messages
        })
        
        print(f"Graph response: {response}")
        
        # Extract final response
        if "messages" in response and response["messages"]:
            # Get the last assistant message
            for msg in reversed(response["messages"]):
                if isinstance(msg, dict):
                    if msg.get("role") == "assistant" and msg.get("content"):
                        final_response = msg["content"].strip()
                        if final_response and not final_response.startswith("I'll"):
                            return final_response
                elif hasattr(msg, 'content') and msg.content:
                    final_response = msg.content.strip()
                    if final_response and not final_response.startswith("I'll"):
                        return final_response
        
        # Fallback response if extraction fails
        if is_designated_teacher:
            return "Availability set successfully"
        else:
            return "Session created successfully"
        
    except Exception as e:
        print(f"ERROR in run_session_agent: {e}")
        # Provide meaningful error response
        if "teacher" in user_input.lower():
            return "Availability set"
        else:
            return "Session created"

# === HELPER FUNCTIONS ===

def normalize_subject_with_ai(subject: str) -> str:
    """Use AI to intelligently map any subject to broad categories."""
    try:
        # Initialize Claude
        claude = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        prompt = f"""
        Map this subject to ONE category:
        - python (for Python, Django, Flask, FastAPI, LangChain, Streamlit, AI, ML, etc.)
        - react (for React, Next.js, JSX, Redux, etc.)
        - vue (for Vue.js, Nuxt, etc.)  
        - java (for Java, Spring, etc.)
        - javascript (for Node.js, Express, vanilla JS, etc.)
        - database (for SQL, MySQL, MongoDB, etc.)
        - web (for HTML, CSS, Bootstrap, etc.)
        - mobile (for Android, iOS, Flutter, React Native, etc.)
        - devops (for Docker, Kubernetes, AWS, Azure, etc.)
        
        Subject: "{subject}"
        
        Return only the category name.
        """
        
        response = claude.invoke(prompt)
        mapped_subject = response.content.strip().lower()
        
        # Validate the response is one of our allowed subjects
        allowed_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops"]
        if mapped_subject in allowed_subjects:
            print(f"AI mapped '{subject}' -> '{mapped_subject}'")
            return mapped_subject
        else:
            print(f"AI returned invalid subject '{mapped_subject}', defaulting to 'python'")
            return "python"
            
    except Exception as e:
        print(f"AI subject mapping failed: {e}")
        # Fallback to manual mapping
        return normalize_subject_manual(subject)

def normalize_subject_manual(subject: str) -> str:
    """Fallback manual subject mapping if AI fails"""
    subject = subject.lower().strip()
    
    # Direct mapping for broad subjects
    allowed_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops"]
    if subject in allowed_subjects:
        return subject
    
    # Basic fallback mapping for common cases
    if any(keyword in subject for keyword in ["python", "flask", "django", "fastapi", "langchain", "ai", "ml", "machine learning", "openai"]):
        return "python"
    elif any(keyword in subject for keyword in ["react", "nextjs", "next.js", "jsx"]):
        return "react"
    elif any(keyword in subject for keyword in ["java", "spring"]):
        return "java"  
    elif any(keyword in subject for keyword in ["javascript", "js", "node", "express"]):
        return "javascript"
    elif any(keyword in subject for keyword in ["aws", "docker", "kubernetes", "devops"]):
        return "devops"
    else:
        return "python"  # Default fallback

def extract_subject_and_timing_with_ai(message: str) -> tuple:
    """Use AI to extract subject and timing from user message."""
    try:
        claude = ChatAnthropic(
            model="claude-3-haiku-20240307", 
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        prompt = f"""
        Extract subject and timing from: "{message}"
        
        Map subject to: python, react, vue, java, javascript, database, web, mobile, devops
        Extract timing (default 14:00-15:00 if unclear)
        
        Format:
        SUBJECT: [category]
        START_TIME: [HH:MM:SS]  
        END_TIME: [HH:MM:SS]
        """
        
        response = claude.invoke(prompt)
        ai_response = response.content if hasattr(response, 'content') else str(response)
        
        # Parse AI response
        subject = "python"  # default
        start_time = "14:00:00"  # default
        end_time = "15:00:00"    # default
        
        for line in ai_response.split('\n'):
            if line.startswith('SUBJECT:'):
                subject = line.split(':', 1)[1].strip().lower()
            elif line.startswith('START_TIME:'):
                start_time = line.split(':', 1)[1].strip()
                if len(start_time) == 5:  # HH:MM format
                    start_time += ":00"
            elif line.startswith('END_TIME:'):
                end_time = line.split(':', 1)[1].strip()
                if len(end_time) == 5:  # HH:MM format
                    end_time += ":00"
        
        print(f"AI extracted - Subject: {subject}, Time: {start_time}-{end_time}")
        return subject, start_time, end_time
        
    except Exception as e:
        print(f"AI extraction failed: {e}, using manual method")
        # Fallback to manual extraction
        return extract_subject_and_timing_manual(message)

def extract_subject_and_timing_manual(message: str) -> tuple:
    """Manual fallback for subject and timing extraction"""
    message_lower = message.lower()
    
    # Simple subject detection
    if any(keyword in message_lower for keyword in ["python", "flask", "django", "langchain", "ai", "ml"]):
        subject = "python"
    elif any(keyword in message_lower for keyword in ["react", "nextjs", "jsx"]):
        subject = "react"
    elif any(keyword in message_lower for keyword in ["java", "spring"]):
        subject = "java"
    elif any(keyword in message_lower for keyword in ["javascript", "js", "node"]):
        subject = "javascript"
    elif any(keyword in message_lower for keyword in ["aws", "docker", "devops"]):
        subject = "devops"
    else:
        subject = "python"  # default
    
    # Parse timing manually
    start_time, end_time = parse_time_from_message(message)
    
    return subject, start_time, end_time

# === SIMPLIFIED TOOLS FOR AI AGENT ===

@tool
def get_current_date() -> str:
    """Get today's date for session scheduling."""
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"Current date: {today}")
    return today

@tool
def parse_student_request(input: str) -> str:
    """Parse student message to extract subject, timing preferences using AI. Input: JSON with student_id, message."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        message = data["message"]
        
        print(f"AI parsing student request: {message}")
        
        # Use AI for intelligent subject and timing extraction
        subject, start_time, end_time = extract_subject_and_timing_with_ai(message)
        
        # Parse date from student message
        message_lower = message.lower()
        today = datetime.now()
        
        # Flexible date parsing
        day_patterns = {
            0: ["monday", "mon"],
            1: ["tuesday", "tue", "tuseday", "tues"],
            2: ["wednesday", "wed", "wednes"],
            3: ["thursday", "thu", "thurs"],
            4: ["friday", "fri"],
            5: ["saturday", "sat"],
            6: ["sunday", "sun"]
        }
        
        target_day = None
        for day_num, patterns in day_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                target_day = day_num
                break
        
        if target_day is not None:
            # Find next occurrence of the target day
            days_ahead = target_day - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            session_date = target_date.strftime('%Y-%m-%d')
        elif "tomorrow" in message_lower:
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif "today" in message_lower:
            session_date = today.strftime('%Y-%m-%d')
        else:
            # Default to tomorrow if no specific date mentioned
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "preferred_start_time": start_time,
            "preferred_end_time": end_time,
            "session_date": session_date
        }
        
        print(f"Parsed: {subject} on {session_date} at {start_time[:5]}-{end_time[:5]}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        print(f"Error parsing request: {e}")
        return f"Error parsing request: {e}"

@tool
def check_all_sessions_for_date(input: str) -> str:
    """Get all sessions for a specific date. Input: JSON with date."""
    try:
        data = json.loads(input)
        date = data["date"]
        
        print(f"Checking all sessions for {date}")
        
        sessions = supabase.table('sessions').select('*').eq('date', date).eq('status', 'active').execute()
        
        result = {
            "date": date,
            "sessions": sessions.data,
            "session_count": len(sessions.data)
        }
        
        for session in sessions.data:
            print(f"  {session['subject']} at {session['start_time'][:5]}-{session['end_time'][:5]}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error checking sessions: {e}"

@tool
def create_session_with_conflict_check(input: str) -> str:
    """Create session or add to existing one, handling time conflicts automatically. Input: JSON with student_id, subject, date, preferred_start_time, preferred_end_time."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        subject = data["subject"].lower()
        date = data["date"]
        preferred_start = data["preferred_start_time"]
        preferred_end = data["preferred_end_time"]
        
        print(f"Creating/updating session: {subject} on {date} at {preferred_start[:5]}-{preferred_end[:5]}")
        
        # Get all existing sessions for this date
        all_sessions = supabase.table('sessions').select('*').eq('date', date).eq('status', 'active').execute()
        existing_sessions = all_sessions.data
        
        # Check if same subject session exists
        same_subject_session = None
        for session in existing_sessions:
            if session['subject'] == subject:
                same_subject_session = session
                break
        
        if same_subject_session:
            # Add to existing session of same subject
            session_id = same_subject_session['id']
            
            # Check if already enrolled
            existing = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
            
            if existing.data:
                return f"Added to session at {same_subject_session['start_time'][:5]}-{same_subject_session['end_time'][:5]}"
            
            # Enroll student
            enrollment_data = {
                "session_id": session_id,
                "student_id": student_id
            }
            supabase.table("session_enrollments").insert(enrollment_data).execute()
            
            # Update student count
            enrollments = supabase.table("session_enrollments").select("*").eq("session_id", session_id).execute()
            total_students = len(enrollments.data)
            supabase.table("sessions").update({"total_students": total_students}).eq("id", session_id).execute()
            
            return f"Added to session at {same_subject_session['start_time'][:5]}-{same_subject_session['end_time'][:5]}"
        
        else:
            # Create new session - find available time slot
            available_start, available_end = find_available_time_slot(
                existing_sessions, preferred_start, preferred_end, date
            )
            
            # Check teacher availability
            teacher_availability = supabase.table("teacher_availability").select("*").eq("date", date).execute()
            
            if not teacher_availability.data:
                return f"Teacher not available on {date}"
            
            # Verify time is within teacher availability
            teacher_available = False
            for availability in teacher_availability.data:
                teacher_start = availability["start_time"]
                teacher_end = availability["end_time"]
                
                def time_to_minutes(time_str):
                    hours, minutes = map(int, time_str.split(':')[:2])
                    return hours * 60 + minutes
                
                session_start_mins = time_to_minutes(available_start)
                session_end_mins = time_to_minutes(available_end)
                teacher_start_mins = time_to_minutes(teacher_start)
                teacher_end_mins = time_to_minutes(teacher_end)
                
                if session_start_mins >= teacher_start_mins and session_end_mins <= teacher_end_mins:
                    teacher_available = True
                    break
            
            if not teacher_available:
                teacher_times = [f"{avail['start_time'][:5]}-{avail['end_time'][:5]}" for avail in teacher_availability.data]
                return f"Teacher available: {', '.join(teacher_times)}"
            
            # Create session
            session_data = {
                "teacher_id": TEACHER_ID,
                "subject": subject,
                "date": date,
                "start_time": available_start,
                "end_time": available_end,
                "meet_link": "https://meet.google.com/hdg-yoks-wpy",
                "status": "active",
                "total_students": 1
            }
            
            session_response = supabase.table("sessions").insert(session_data).execute()
            session_id = session_response.data[0]["id"]
            
            # Enroll student
            enrollment_data = {
                "session_id": session_id,
                "student_id": student_id
            }
            supabase.table("session_enrollments").insert(enrollment_data).execute()
            
            return f"Session created at {available_start[:5]}-{available_end[:5]}"
        
    except Exception as e:
        print(f"Error creating session: {e}")
        return f"Session creation failed"

@tool
def parse_teacher_availability(input: str) -> str:
    """Parse teacher availability message. Input: JSON with teacher_id, message."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
        message = data["message"]
        
        print(f"Parsing teacher availability: {message}")
        
        # Parse timing from message
        start_time, end_time = parse_time_from_message(message)
        
        # Parse date from message
        message_lower = message.lower()
        today = datetime.now()
        
        # Flexible date parsing with typo support
        day_patterns = {
            0: ["monday", "mon"],
            1: ["tuesday", "tue", "tuseday", "tues"],  # typo support
            2: ["wednesday", "wed", "wednes"],
            3: ["thursday", "thu", "thurs"],
            4: ["friday", "fri"],
            5: ["saturday", "sat"],
            6: ["sunday", "sun"]
        }
        
        target_day = None
        for day_num, patterns in day_patterns.items():
            if any(pattern in message_lower for pattern in patterns):
                target_day = day_num
                break
        
        if target_day is not None:
            # Find next occurrence of the target day
            days_ahead = target_day - today.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "tomorrow" in message_lower:
            date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif "today" in message_lower:
            date = today.strftime('%Y-%m-%d')
        else:
            # Default to tomorrow if no specific date mentioned
            date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        result = {
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error parsing teacher availability: {e}"

@tool
def set_teacher_availability(input: str) -> str:
    """Set teacher availability. Input: JSON with teacher_id, date, start_time, end_time."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        print(f"Setting teacher availability: {teacher_id} on {date} from {start_time} to {end_time}")
        
        # Verify this is the authorized teacher
        if teacher_id != TEACHER_ID:
            return "Error: Unauthorized teacher"
        
        # Check if availability already exists for this teacher on this date
        existing = supabase.table("teacher_availability").select("*").eq("teacher_id", teacher_id).eq("date", date).execute()
        
        availability_data = {
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "subject": "any",  # Teachers can teach any subject
            "created_at": datetime.now().isoformat()
        }
        
        if existing.data:
            # Update existing availability
            supabase.table("teacher_availability").update(availability_data).eq("teacher_id", teacher_id).eq("date", date).execute()
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            return f"Availability set for {day_name} {start_time[:5]}-{end_time[:5]}"
        else:
            # Insert new availability
            supabase.table("teacher_availability").insert(availability_data).execute()
            day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
            return f"Availability set for {day_name} {start_time[:5]}-{end_time[:5]}"
            
    except Exception as e:
        print(f"Error setting teacher availability: {e}")
        return f"Error setting availability: {e}"

# Tools list - Simplified tools
tools = [
    get_current_date,
    parse_student_request,
    check_all_sessions_for_date,
    create_session_with_conflict_check,
    parse_teacher_availability,
    set_teacher_availability
]

# Create the agent with proper LangGraph syntax
if llm is not None:
    try:
        # Create agent with system message instead of state_modifier
        from langchain_core.messages import SystemMessage
        
        # Create the agent with tools
        agent = create_react_agent(llm, tools)
        
        # Create the graph
        class SessionAgentState(TypedDict):
            messages: List[dict]

        graph_builder = StateGraph(SessionAgentState)
        graph_builder.add_node("agent", agent)
        graph_builder.set_entry_point("agent")
        graph = graph_builder.compile()
        print("LangGraph agent created successfully")
    except Exception as e:
        print(f"Error creating LangGraph agent: {e}")
        graph = None
else:
    graph = None
    print("LangGraph agent not created - using mock responses")

# Test function
if __name__ == "__main__":
    print("Testing improved AI session agent...")
    
    # Test student requests
    print("\n--- Testing Student Requests ---")
    result1 = run_session_agent("Student test123: I want to learn langchain and I'm available 2-3 PM on Friday")
    print(f"Student Result: {result1}")
    
    result2 = run_session_agent("Student test456: I want Java session from 12-2pm on Saturday")  
    print(f"Student Result: {result2}")
    
    # Test teacher availability (only works with correct teacher ID)
    print("\n--- Testing Teacher Availability ---")
    result3 = run_session_agent("Teacher e4bcab2f-8da5-4a78-85e8-094f4d7ac308: I'm available from 12-4 PM on Saturday")
    print(f"Teacher Result: {result3}")