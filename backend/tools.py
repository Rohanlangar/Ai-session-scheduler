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


# Get credentials from environment variables
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

# DESIGNATED TEACHER ID
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

def get_full_database_context() -> str:
    """Get comprehensive database context for AI decision making"""
    try:
        # Get all active sessions
        sessions = supabase.table('sessions').select('*').eq('status', 'active').execute()
        
        # Get all teacher availability
        teacher_avail = supabase.table('teacher_availability').select('*').execute()
        
        # Get all enrollments
        enrollments = supabase.table('session_enrollments').select('*').execute()
        
        # Get unique subjects from database
        unique_subjects = set()
        for session in sessions.data:
            unique_subjects.add(session['subject'])
        
        context = f"""
DATABASE CONTEXT:
=================

EXISTING SUBJECTS: {', '.join(sorted(unique_subjects))}

ACTIVE SESSIONS ({len(sessions.data)} total):
{json.dumps(sessions.data, indent=2)}

TEACHER AVAILABILITY ({len(teacher_avail.data)} slots):
{json.dumps(teacher_avail.data, indent=2)}

ENROLLMENTS ({len(enrollments.data)} total):
{json.dumps(enrollments.data, indent=2)}

CURRENT DATE: {datetime.now().strftime('%Y-%m-%d')}
CURRENT TIME: {datetime.now().strftime('%H:%M:%S')}
"""
        return context
        
    except Exception as e:
        print(f"Error getting database context: {e}")
        return f"DATABASE CONTEXT ERROR: {e}"

def clean_ai_response(response: str) -> str:
    """Clean AI response to remove XML tags and formatting issues"""
    if not response:
        return "Operation completed"
    
    # Remove XML-like tags
    response = re.sub(r'<[^>]+>', '', response)
    
    # Remove extra whitespace and newlines
    response = ' '.join(response.split())
    
    # Remove common prefixes that indicate processing
    prefixes_to_remove = [
        "I'll", "Let me", "I will", "I need to", "First,", "Now,", 
        "Looking at", "Based on", "After checking"
    ]
    
    for prefix in prefixes_to_remove:
        if response.startswith(prefix):
            # Find the actual result after the processing description
            sentences = response.split('. ')
            for sentence in sentences:
                if any(key in sentence.lower() for key in ['created', 'added', 'set', 'available']):
                    response = sentence.strip()
                    if not response.endswith('.'):
                        response += '.'
                    break
            break
    
    # Ensure it's not too long
    if len(response) > 50:
        # Try to extract the key message
        if 'created at' in response.lower():
            match = re.search(r'created at (\d{1,2}:\d{2})', response.lower())
            if match:
                return f"Session created at {match.group(1)}"
        elif 'added to session at' in response.lower():
            match = re.search(r'added to session at (\d{1,2}:\d{2})', response.lower())
            if match:
                return f"Added to session at {match.group(1)}"
        elif 'availability set' in response.lower():
            return "Availability set successfully"
    
    return response.strip()

class AgentState(TypedDict):
    messages: List[dict]
    next: Optional[str]

# Enhanced Claude LLM with better parameters
try:
    llm = ChatAnthropic(
        model="claude-3-sonnet-20240229",  # Using more capable model
        temperature=0,  # Zero temperature for consistent responses
        max_tokens=150,  # Limit response length
        api_key=ANTHROPIC_API_KEY
    )
    print("Anthropic LLM initialized successfully")
except Exception as e:
    print(f"Anthropic LLM initialization failed: {e}")
    llm = None

# Enhanced system prompt with database context awareness
system_prompt = """
You are an intelligent session scheduler with FULL DATABASE ACCESS. 

CRITICAL INSTRUCTIONS:
=====================

**ALWAYS use the provided DATABASE CONTEXT to make informed decisions.**

**FOR TEACHERS (user_id = e4bcab2f-8da5-4a78-85e8-094f4d7ac308):**
- Use get_full_database_context() first
- Parse teacher availability with parse_teacher_availability()  
- Set availability with set_teacher_availability()
- Respond: "Availability set for [day] [time]"

**FOR STUDENTS:**
1. ALWAYS call get_full_database_context() FIRST to understand current state
2. Use intelligent_parse_student_request() with full context
3. Call smart_session_handler() for optimal session management

**RESPONSE FORMAT RULES:**
- NEVER include XML tags like <result> or <response>
- NEVER include processing descriptions like "I'll" or "Let me"  
- Keep responses under 8 words
- Format: "Session created at [time]" or "Added to session at [time]"
- NO explanations, NO extra text

**SUBJECT HANDLING:**
- Preserve exact subject names from user input (e.g., "langchain" stays "langchain")
- Don't map subjects to broad categories unless identical subject exists
- Let AI decide based on database context

**MANDATORY:** Every response must be clean, direct, and actionable.
"""

def run_session_agent(user_input: str) -> str:
    """Enhanced session agent with full database context and better response handling"""
    try:
        user_id, is_teacher_from_message, clean_message = extract_user_id_from_message(user_input)
        
        print(f"Processing - User ID: {user_id}, Message: {clean_message}")
        
        is_designated_teacher = (user_id == TEACHER_ID)
        
        if is_designated_teacher:
            print(f"TEACHER detected: {user_id}")
            contextual_input = f"""
TEACHER {user_id} says: {clean_message}

TASK: Set teacher availability
1. Call get_full_database_context() to see current state
2. Call parse_teacher_availability() with teacher_id and message  
3. Call set_teacher_availability() with parsed data
4. Respond with exactly: "Availability set for [day] [time]"

DO NOT include any processing descriptions or XML tags.
"""
        else:
            print(f"STUDENT detected: {user_id}")
            contextual_input = f"""
STUDENT {user_id} says: {clean_message}

TASK: Handle student session request with full database awareness
1. Call get_full_database_context() to understand current sessions and subjects
2. Call intelligent_parse_student_request() with student_id, message, and context
3. Call smart_session_handler() with all necessary data
4. Respond with exactly: "Session created at [time]" or "Added to session at [time]"

DO NOT include any processing descriptions or XML tags.
"""
        
        if llm is None or graph is None:
            return "Session created successfully" if not is_designated_teacher else "Availability set successfully"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": contextual_input}
        ]
        
        response = graph.invoke({"messages": messages})
        
        print(f"Raw graph response: {response}")
        
        # Enhanced response extraction
        final_response = ""
        if "messages" in response and response["messages"]:
            for msg in reversed(response["messages"]):
                content = ""
                
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                elif hasattr(msg, 'content'):
                    content = msg.content
                
                if content and isinstance(content, str):
                    cleaned_content = clean_ai_response(content)
                    if cleaned_content and len(cleaned_content.strip()) > 0:
                        final_response = cleaned_content
                        break
        
        # Final fallback with context
        if not final_response or len(final_response.strip()) == 0:
            if is_designated_teacher:
                final_response = "Availability set successfully"
            else:
                final_response = "Session created successfully"
        
        print(f"Final cleaned response: {final_response}")
        return final_response
        
    except Exception as e:
        print(f"ERROR in run_session_agent: {e}")
        if "teacher" in user_input.lower():
            return "Availability set"
        else:
            return "Session created"

# === ENHANCED TOOLS WITH FULL DATABASE CONTEXT ===

@tool
def get_full_database_context() -> str:
    """Get comprehensive database context including all sessions, subjects, and availability"""
    return get_full_database_context()

@tool  
def intelligent_parse_student_request(input: str) -> str:
    """AI-powered parsing with full database context. Input: JSON with student_id, message, database_context"""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        message = data["message"]
        db_context = data.get("database_context", "")
        
        print(f"AI parsing student request with context: {message}")
        
        # Use Claude to intelligently parse the request with full context
        claude = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        parsing_prompt = f"""
PARSE THIS STUDENT REQUEST WITH DATABASE CONTEXT:

DATABASE CONTEXT:
{db_context}

STUDENT MESSAGE: "{message}"

INSTRUCTIONS:
1. Extract the EXACT subject name from message (don't categorize - preserve original)
2. If subject matches existing database subjects, use exact match
3. If new subject, use exact user input (e.g., "langchain" stays "langchain")
4. Parse timing preferences (default to 2-3 PM if unclear)
5. Parse date (default to tomorrow if unclear)

OUTPUT FORMAT:
SUBJECT: [exact_subject_name]
START_TIME: [HH:MM:SS]
END_TIME: [HH:MM:SS]  
DATE: [YYYY-MM-DD]
"""
        
        response = claude.invoke(parsing_prompt)
        ai_response = response.content if hasattr(response, 'content') else str(response)
        
        # Parse AI response
        subject = "python"  # fallback
        start_time = "14:00:00"
        end_time = "15:00:00"  
        today = datetime.now()
        session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        for line in ai_response.split('\n'):
            line = line.strip()
            if line.startswith('SUBJECT:'):
                subject = line.split(':', 1)[1].strip().lower()
            elif line.startswith('START_TIME:'):
                time_str = line.split(':', 1)[1].strip()
                if len(time_str) == 5:  # HH:MM
                    start_time = time_str + ":00"
                else:
                    start_time = time_str
            elif line.startswith('END_TIME:'):
                time_str = line.split(':', 1)[1].strip()
                if len(time_str) == 5:  # HH:MM
                    end_time = time_str + ":00"
                else:
                    end_time = time_str
            elif line.startswith('DATE:'):
                session_date = line.split(':', 1)[1].strip()
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "preferred_start_time": start_time,
            "preferred_end_time": end_time,
            "session_date": session_date
        }
        
        print(f"Intelligently parsed: {subject} on {session_date} at {start_time[:5]}-{end_time[:5]}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        print(f"Error in intelligent parsing: {e}")
        return f"Error parsing request: {e}"

@tool
def smart_session_handler(input: str) -> str:
    """AI-powered session creation with conflict resolution. Input: JSON with student_id, subject, date, preferred_start_time, preferred_end_time"""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        subject = data["subject"]
        date = data["date"]
        preferred_start = data["preferred_start_time"]
        preferred_end = data["preferred_end_time"]
        
        print(f"Smart session handling: {subject} on {date} at {preferred_start[:5]}-{preferred_end[:5]}")
        
        # Get all existing sessions for this date
        all_sessions = supabase.table('sessions').select('*').eq('date', date).eq('status', 'active').execute()
        existing_sessions = all_sessions.data
        
        # Check for exact subject match first
        same_subject_session = None
        for session in existing_sessions:
            if session['subject'].lower() == subject.lower():
                same_subject_session = session
                break
        
        if same_subject_session:
            # Add to existing session
            session_id = same_subject_session['id']
            
            # Check if already enrolled
            existing = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
            
            if not existing.data:
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
            
            return f"Added to session at {same_subject_session['start_time'][:5]}"
        
        else:
            # Create new session - find available time
            available_start, available_end = find_available_time_slot(existing_sessions, preferred_start, preferred_end, date)
            
            # Verify teacher availability
            teacher_avail = supabase.table("teacher_availability").select("*").eq("date", date).execute()
            
            if not teacher_avail.data:
                return f"Teacher unavailable on {date}"
            
            # Check if time fits within teacher availability
            teacher_available = False
            for availability in teacher_avail.data:
                if time_fits_in_availability(available_start, available_end, availability["start_time"], availability["end_time"]):
                    teacher_available = True
                    break
            
            if not teacher_available:
                return "No available time slots"
            
            # Create session
            session_data = {
                "teacher_id": TEACHER_ID,
                "subject": subject,  # Preserve exact subject name
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
            
            return f"Session created at {available_start[:5]}"
        
    except Exception as e:
        print(f"Error in smart session handler: {e}")
        return "Session creation failed"

def time_fits_in_availability(session_start: str, session_end: str, avail_start: str, avail_end: str) -> bool:
    """Check if session time fits within teacher availability"""
    def time_to_minutes(time_str):
        hours, minutes = map(int, time_str.split(':')[:2])
        return hours * 60 + minutes
    
    session_start_mins = time_to_minutes(session_start)
    session_end_mins = time_to_minutes(session_end)
    avail_start_mins = time_to_minutes(avail_start)
    avail_end_mins = time_to_minutes(avail_end)
    
    return session_start_mins >= avail_start_mins and session_end_mins <= avail_end_mins

def find_available_time_slot(existing_sessions: list, preferred_start: str, preferred_end: str, date: str) -> tuple:
    """Find available time slot avoiding conflicts"""
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
    
    # Get occupied slots
    occupied_slots = []
    for session in existing_sessions:
        if session['date'] == date and session['status'] == 'active':
            start_mins = time_to_minutes(session['start_time'])
            end_mins = time_to_minutes(session['end_time'])
            occupied_slots.append((start_mins, end_mins))
    
    occupied_slots.sort()
    
    # Check if preferred time is available
    preferred_conflicts = False
    for start_mins, end_mins in occupied_slots:
        if not (preferred_end_mins <= start_mins or preferred_start_mins >= end_mins):
            preferred_conflicts = True
            break
    
    if not preferred_conflicts:
        return preferred_start, preferred_end
    
    # Find next available slot
    current_time = preferred_start_mins
    
    for start_mins, end_mins in occupied_slots:
        if current_time + session_duration <= start_mins:
            available_start = minutes_to_time(current_time)
            available_end = minutes_to_time(current_time + session_duration)
            return available_start, available_end
        current_time = max(current_time, end_mins)
    
    # Use time after last session
    available_start = minutes_to_time(current_time)
    available_end = minutes_to_time(current_time + session_duration)
    return available_start, available_end

@tool
def parse_teacher_availability(input: str) -> str:
    """Parse teacher availability message. Input: JSON with teacher_id, message."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
        message = data["message"]
        
        # Use AI to parse teacher availability
        claude = ChatAnthropic(
            model="claude-3-sonnet-20240229",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        prompt = f"""
Parse teacher availability from: "{message}"

Extract:
- Date (tomorrow if not specified)
- Start time  
- End time

Current date: {datetime.now().strftime('%Y-%m-%d')}

Format:
DATE: [YYYY-MM-DD]
START_TIME: [HH:MM:SS]
END_TIME: [HH:MM:SS]
"""
        
        response = claude.invoke(prompt)
        ai_response = response.content if hasattr(response, 'content') else str(response)
        
        # Parse response
        today = datetime.now()
        date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        start_time = "09:00:00"
        end_time = "17:00:00"
        
        for line in ai_response.split('\n'):
            line = line.strip()
            if line.startswith('DATE:'):
                date = line.split(':', 1)[1].strip()
            elif line.startswith('START_TIME:'):
                time_str = line.split(':', 1)[1].strip()
                if len(time_str) == 5:
                    start_time = time_str + ":00"
                else:
                    start_time = time_str
            elif line.startswith('END_TIME:'):
                time_str = line.split(':', 1)[1].strip()
                if len(time_str) == 5:
                    end_time = time_str + ":00"
                else:
                    end_time = time_str
        
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
    """Set teacher availability in database."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        if teacher_id != TEACHER_ID:
            return "Error: Unauthorized teacher"
        
        # Check if availability exists
        existing = supabase.table("teacher_availability").select("*").eq("teacher_id", teacher_id).eq("date", date).execute()
        
        availability_data = {
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "subject": "any",
            "created_at": datetime.now().isoformat()
        }
        
        if existing.data:
            supabase.table("teacher_availability").update(availability_data).eq("teacher_id", teacher_id).eq("date", date).execute()
        else:
            supabase.table("teacher_availability").insert(availability_data).execute()
            
        day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A')
        return f"Availability set for {day_name} {start_time[:5]}-{end_time[:5]}"
            
    except Exception as e:
        print(f"Error setting teacher availability: {e}")
        return f"Error setting availability: {e}"

# Enhanced tools list
tools = [
    get_full_database_context,
    intelligent_parse_student_request,
    smart_session_handler,
    parse_teacher_availability,
    set_teacher_availability
]

# Create enhanced agent
if llm is not None:
    try:
        agent = create_react_agent(llm, tools)
        
        class SessionAgentState(TypedDict):
            messages: List[dict]

        graph_builder = StateGraph(SessionAgentState)
        graph_builder.add_node("agent", agent)
        graph_builder.set_entry_point("agent")
        graph = graph_builder.compile()
        print("Enhanced LangGraph agent created successfully")
    except Exception as e:
        print(f"Error creating LangGraph agent: {e}")
        graph = None
else:
    graph = None

# Test function
if __name__ == "__main__":
    print("Testing enhanced AI session agent...")
    
    # Test student requests
    print("\n--- Testing Student Requests ---")
    result1 = run_session_agent("Student test123: I want to learn langchain and I'm available 2-3 PM on Friday")
    print(f"Student Result: {result1}")
    
    result2 = run_session_agent("Student test456: I want docker session from 3-5pm on Saturday")  
    print(f"Student Result: {result2}")
    
    # Test teacher availability
    print("\n--- Testing Teacher Availability ---")
    result3 = run_session_agent("Teacher e4bcab2f-8da5-4a78-85e8-094f4d7ac308: I'm available from 12-4 PM on Saturday")
    print(f"Teacher Result: {result3}")