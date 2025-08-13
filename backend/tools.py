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
# Load environment variables

# Get credentials from environment variables with fallbacks
SUPABASE_URL = os.getenv("SUPABASE_URL") 
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"🔧 Using Supabase URL: {SUPABASE_URL}")
print(f"🔧 Using Anthropic API: {'✅ Set' if ANTHROPIC_API_KEY else '❌ Missing'}")

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    """Extract time information from user message"""
    # Look for time patterns like "2-3 PM", "1:30-2:30", "2 to 3 PM"
    time_patterns = [
        r'(\d{1,2}):?(\d{0,2})\s*-\s*(\d{1,2}):?(\d{0,2})\s*(am|pm)?',
        r'(\d{1,2})\s*to\s*(\d{1,2})\s*(am|pm)?',
        r'(\d{1,2})\s*(am|pm)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message.lower())
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                start_hour = int(groups[0])
                end_hour = int(groups[2]) if len(groups) > 2 and groups[2] else start_hour + 1
                
                # Handle PM conversion
                if 'pm' in message.lower() and start_hour < 12:
                    start_hour += 12
                    end_hour += 12
                elif 'am' in message.lower() and start_hour == 12:
                    start_hour = 0
                
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
    
    # Default fallback
    return "14:00:00", "15:00:00"

def calculate_optimal_timing(student_timings: list, teacher_availability: tuple = ("09:00:00", "21:00:00")) -> tuple:
    """Calculate optimal session timing considering all students and teacher availability"""
    if not student_timings:
        return "14:00:00", "15:00:00"
    
    print(f"🔍 Calculating optimal timing for {len(student_timings)} students")
    
    # Convert all times to minutes for easier calculation
    time_ranges = []
    for start_str, end_str in student_timings:
        start_mins = int(start_str.split(':')[0]) * 60 + int(start_str.split(':')[1])
        end_mins = int(end_str.split(':')[0]) * 60 + int(end_str.split(':')[1])
        time_ranges.append((start_mins, end_mins))
        print(f"  Student timing: {start_str} - {end_str}")
    
    # Find the overlap or best compromise
    all_starts = [r[0] for r in time_ranges]
    all_ends = [r[1] for r in time_ranges]
    
    # Calculate average start and end times
    avg_start = sum(all_starts) // len(all_starts)
    avg_end = sum(all_ends) // len(all_ends)
    
    # Ensure minimum 1 hour duration
    if avg_end - avg_start < 60:
        avg_end = avg_start + 60
    
    # Convert back to time format
    start_hour = avg_start // 60
    start_min = avg_start % 60
    end_hour = avg_end // 60
    end_min = avg_end % 60
    
    optimal_start = f"{start_hour:02d}:{start_min:02d}:00"
    optimal_end = f"{end_hour:02d}:{end_min:02d}:00"
    
    print(f"🎯 Optimal timing: {optimal_start} - {optimal_end}")
    return optimal_start, optimal_end

# --- LangGraph Setup ---
class AgentState(TypedDict):
    messages: List[dict]
    next: Optional[str]

# Claude (Anthropic) LLM
llm = ChatAnthropic(
    model="claude-3-haiku-20240307",
    temperature=0.1,
    api_key=ANTHROPIC_API_KEY
)

# System prompt for the agent
system_prompt = """
You are an intelligent AI session scheduler. Help students book sessions and teachers set availability.

**FOR STUDENTS (message starts with "Student"):**
1. **Call get_current_date()** to get today's date
2. **Call parse_student_request()** to extract subject and timing from student message
3. **Call check_existing_session()** with the subject and today's date
4. **If session exists (exists=True):** Call update_existing_session() to add student
5. **If session doesn't exist (exists=False):** Call create_new_session()

**FOR TEACHERS (contextual input mentions "TEACHER"):**
1. **Call parse_teacher_availability()** to extract teacher_id, date, and timing
2. **Call set_teacher_availability()** with the parsed data
3. **NEVER call student session tools for teachers**
4. **Keep responses short:** "✅ Availability set for [date] from [time] to [time]"

**Subject mapping (normalize to lowercase)border subject not specific concept:**
- Flask/Django/FastAPI/Python → "python"
- React/Vue/JSX → "react"  
- Spring/Hibernate → "java"
- Node.js/Express → "javascript"

**CRITICAL RULES:**
- If input mentions "TEACHER" → ONLY use teacher tools (parse_teacher_availability, set_teacher_availability)
- If input mentions "STUDENT" → ONLY use student tools (parse_student_request, check_existing_session, etc.)
- NEVER mix teacher and student workflows
- Teachers set availability, students book sessions
- Keep responses short and friendly

**IMPORTANT:** 
- Teachers: Use parse_teacher_availability() first, then set_teacher_availability()
- Students: Use student workflow for session booking
- If missing essential information, ask for proper format 
"""

def run_session_agent(user_input: str) -> str:
    """Run the session creation agent with user input."""
    try:
        # Extract user information from the message
        user_id, is_teacher_from_message, clean_message = extract_user_id_from_message(user_input)
        
        print(f"🔍 Processing - User ID: {user_id}, Message: {clean_message}")
        
        # Check if user is actually a teacher by checking teachers table
        teacher_check = supabase.table("teachers").select("id").eq("id", user_id).execute()
        is_actual_teacher = bool(teacher_check.data)
        
        print(f"🔍 Teacher check: {is_actual_teacher} (found in teachers table: {len(teacher_check.data) > 0})")
        
        if is_actual_teacher:
            # This is a teacher - handle availability setting
            contextual_input = f"""
Teacher {user_id} says: {clean_message}

This is a TEACHER setting availability. Follow teacher workflow:
1. Get current date
2. Parse the availability message for date and timing
3. Call set_teacher_availability() ONLY
4. Do NOT call any student session tools

Keep response short and friendly!
"""
        else:
            # This is a student - handle session booking
            contextual_input = f"""
Student {user_id} wants: {clean_message}

This is a STUDENT booking sessions. Follow student workflow:
1. Get current date
2. Get all sessions data  
3. Check if session exists for same subject/date
4. Create new session OR update existing session with optimal timing

Keep response short and friendly!
"""
        
        response = graph.invoke({
            "messages": [{"role": "user", "content": contextual_input}]
        })
        
        # Extract the final AI message
        final_message = response["messages"][-1]
        return final_message.content if hasattr(final_message, 'content') else str(final_message)
        
    except Exception as e:
        print(f"❌ ERROR in run_session_agent: {e}")
        return f"I understand you want to help. Let me assist you with that!"

# === HELPER FUNCTIONS ===

def extract_subject_and_timing(message: str) -> tuple:
    """Extract subject and timing from user message"""
    message_lower = message.lower()
    
    # Determine subject
    subject = "python"  # default
    if any(word in message_lower for word in ["react", "vue", "jsx"]):
        subject = "react"
    elif any(word in message_lower for word in ["java", "spring", "hibernate"]):
        subject = "java"
    elif any(word in message_lower for word in ["javascript", "node", "express"]):
        subject = "javascript"
    elif any(word in message_lower for word in ["python", "flask", "django", "fastapi"]):
        subject = "python"
    
    # Parse timing
    start_time, end_time = parse_time_from_message(message)
    
    return subject, start_time, end_time

# === SIMPLIFIED TOOLS FOR AI AGENT ===

@tool
def get_current_date() -> str:
    """Get today's date for session scheduling."""
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"� CurGrent date: {today}")
    return today

@tool
def get_all_sessions_data() -> str:
    """Get all current sessions and enrollments data."""
    try:
        print("🔄 Getting sessions data...")
        
        # Get sessions and enrollments
        sessions = supabase.table('sessions').select('*').eq('status', 'active').execute()
        enrollments = supabase.table('session_enrollments').select('*').execute()
        student_availability = supabase.table('student_availability').select('*').execute()
        
        data = {
            'active_sessions': sessions.data,
            'enrollments': enrollments.data,
            'student_availability': student_availability.data,
            'summary': f"Found {len(sessions.data)} active sessions with {len(enrollments.data)} total enrollments"
        }
        
        print(f"✅ Sessions data loaded: {len(sessions.data)} sessions")
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        return f"Error getting sessions data: {e}"

@tool
def parse_student_request(input: str) -> str:
    """Parse student message to extract subject, timing preferences. Input: JSON with student_id, message."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        message = data["message"]
        
        # VALIDATION: Check if message contains proper timing information
        message_lower = message.lower()
        
        # Check for time patterns
        time_patterns = [
            r'\d{1,2}:?\d{0,2}\s*-\s*\d{1,2}:?\d{0,2}\s*(am|pm)?',
            r'\d{1,2}\s*to\s*\d{1,2}\s*(am|pm)?',
            r'\d{1,2}\s*(am|pm)',
        ]
        
        has_timing = any(re.search(pattern, message_lower) for pattern in time_patterns)
        
        # Check for subject keywords
        subject_keywords = ["python", "react", "java", "javascript", "flask", "django", "fastapi", "vue", "jsx", "spring", "hibernate", "node", "express"]
        has_subject = any(keyword in message_lower for keyword in subject_keywords)
        
        # If missing essential information, return validation error
        if not has_timing and not has_subject:
            return json.dumps({
                "validation_error": True,
                "message": "Please provide a properly formatted message that includes both subject and timing. Example: 'I want Python session 2-3 PM' or 'React session from 1:30 to 2:30 PM'"
            })
        elif not has_timing:
            return json.dumps({
                "validation_error": True,
                "message": "Please specify the timing for your session. Example: '2-3 PM' or '1:30 to 2:30 PM'"
            })
        elif not has_subject:
            return json.dumps({
                "validation_error": True,
                "message": "Please specify the subject you want to learn. Available subjects: Python, React, Java, JavaScript"
            })
        
        # If validation passes, proceed with parsing
        subject, start_time, end_time = extract_subject_and_timing(message)
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "preferred_start_time": start_time,
            "preferred_end_time": end_time,
            "parsed_message": f"Student {student_id} wants {subject} session from {start_time[:5]} to {end_time[:5]}"
        }
        
        print(f"📝 Parsed request: {result['parsed_message']}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error parsing request: {e}"

@tool
def check_existing_session(input: str) -> str:
    """Check if session exists for specific subject and date. Input: JSON with subject, date."""
    try:
        data = json.loads(input)
        subject = data["subject"].lower()
        date = data["date"]
        
        print(f"🔍 Checking for {subject} session on {date}")
        
        sessions = supabase.table('sessions').select('*').eq('subject', subject).eq('date', date).eq('status', 'active').execute()
        
        if sessions.data:
            session = sessions.data[0]
            result = {
                "exists": True,
                "session_id": session["id"],
                "current_timing": f"{session['start_time']}-{session['end_time']}",
                "student_count": session["total_students"],
                "message": f"Found {subject} session on {date} at {session['start_time'][:5]}-{session['end_time'][:5]}"
            }
            print(f"✅ Found existing session: {result['message']}")
        else:
            result = {
                "exists": False,
                "message": f"No {subject} session found for {date}"
            }
            print(f"❌ No existing session found")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error checking existing session: {e}"

@tool
def create_new_session(input: str) -> str:
    """Create a new session. Input: JSON with student_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        subject = data["subject"].lower()
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        print(f"🆕 Creating new {subject} session for {date} at {start_time}-{end_time}")
        
        # 1. Store student availability
        availability_data = {
            "student_id": student_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "subject": subject
        }
        supabase.table("student_availability").insert(availability_data).execute()
        
        # 2. Create session
        session_data = {
            "teacher_id": "46a3bfcd-2d45-417c-b578-b4ac0f1c577c",
            "subject": subject,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "meet_link": "https://meet.google.com/hdg-yoks-wpy",
            "status": "active",
            "total_students": 1
        }
        
        session_response = supabase.table("sessions").insert(session_data).execute()
        session_id = session_response.data[0]["id"]
        
        # 3. Enroll student
        enrollment_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        supabase.table("session_enrollments").insert(enrollment_data).execute()
        
        # 4. Update availability with session_id
        supabase.table("student_availability").update({"session_id": session_id}).eq("student_id", student_id).eq("date", date).eq("subject", subject).execute()
        
        print(f"✅ Session created with ID: {session_id}")
        return f"✅ {subject.title()} session created at {start_time[:5]}-{end_time[:5]} (1 student)"
        
    except Exception as e:
        print(f"❌ Error creating session: {e}")
        return f"Error creating session: {e}"

@tool
def update_existing_session(input: str) -> str:
    """Add student to existing session and optimize timing. Input: JSON with session_id, student_id, preferred_start_time, preferred_end_time, subject, date."""
    try:
        data = json.loads(input)
        session_id = data["session_id"]
        student_id = data["student_id"]
        preferred_start = data["preferred_start_time"]
        preferred_end = data["preferred_end_time"]
        subject = data["subject"].lower()
        date = data["date"]
        
        print(f"🔄 Updating session {session_id} with new student {student_id}")
        
        # Check if already enrolled
        existing = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
        
        if existing.data:
            print(f"⚠️ Student already enrolled")
            return f"✅ You're already enrolled in this {subject} session!"
        
        # 1. Store student availability
        availability_data = {
            "student_id": student_id,
            "date": date,
            "start_time": preferred_start,
            "end_time": preferred_end,
            "subject": subject,
            "session_id": session_id
        }
        supabase.table("student_availability").insert(availability_data).execute()
        
        # 2. Enroll student
        enrollment_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        supabase.table("session_enrollments").insert(enrollment_data).execute()
        
        # 3. Get all student timings for this session to calculate optimal time
        all_availability = supabase.table("student_availability").select("start_time, end_time").eq("session_id", session_id).execute()
        
        student_timings = [(avail["start_time"], avail["end_time"]) for avail in all_availability.data]
        
        # 4. Calculate optimal timing
        optimal_start, optimal_end = calculate_optimal_timing(student_timings)
        
        # 5. Update session timing
        supabase.table("sessions").update({
            "start_time": optimal_start,
            "end_time": optimal_end
        }).eq("id", session_id).execute()
        
        # 6. Update student count
        enrollments = supabase.table("session_enrollments").select("*").eq("session_id", session_id).execute()
        total_students = len(enrollments.data)
        supabase.table("sessions").update({"total_students": total_students}).eq("id", session_id).execute()
        
        print(f"✅ Session updated: {optimal_start}-{optimal_end}, {total_students} students")
        return f"✅ {subject.title()} session updated to {optimal_start[:5]}-{optimal_end[:5]} ({total_students} students)"
        
    except Exception as e:
        print(f"❌ Error updating session: {e}")
        return f"Error updating session: {e}"

@tool
def parse_teacher_availability(input: str) -> str:
    """Parse teacher availability message. Input: JSON with teacher_id, message."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
        message = data["message"]
        
        print(f"📝 Parsing teacher availability: {message}")
        
        # Parse timing from message
        start_time, end_time = parse_time_from_message(message)
        
        # Parse date from message
        message_lower = message.lower()
        today = datetime.now()
        
        # Simple date parsing
        if "friday" in message_lower:
            # Find next Friday
            days_ahead = 4 - today.weekday()  # Friday is 4
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
            "end_time": end_time,
            "parsed_message": f"Teacher {teacher_id} available on {date} from {start_time[:5]} to {end_time[:5]}"
        }
        
        print(f"📝 Parsed teacher availability: {result['parsed_message']}")
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
        
        print(f"📅 Setting teacher availability: {teacher_id} on {date} from {start_time} to {end_time}")
        
        # First check if teacher_id exists in teachers table
        teacher_check = supabase.table("teachers").select("id").eq("id", teacher_id).execute()
        
        if not teacher_check.data:
            print(f"❌ Teacher ID {teacher_id} not found in teachers table")
            return "❌ Error: You must be a registered teacher to set availability"
        
        print(f"✅ Teacher verified: {teacher_id}")
        
        # Check if availability already exists for this teacher on this date
        existing = supabase.table("teacher_availability").select("*").eq("teacher_id", teacher_id).eq("date", date).execute()
        
        availability_data = {
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "subject": "any",  # Default subject as requested
            "created_at": datetime.now().isoformat()
        }
        
        if existing.data:
            # Update existing availability
            supabase.table("teacher_availability").update(availability_data).eq("teacher_id", teacher_id).eq("date", date).execute()
            print(f"✅ Updated teacher availability for {date}")
            return f"✅ Updated your availability for {date} from {start_time[:5]} to {end_time[:5]}"
        else:
            # Insert new availability
            supabase.table("teacher_availability").insert(availability_data).execute()
            print(f"✅ Added teacher availability for {date}")
            return f"✅ Added your availability for {date} from {start_time[:5]} to {end_time[:5]}"
            
    except Exception as e:
        print(f"❌ Error setting teacher availability: {e}")
        return f"❌ Error setting availability: {e}"

# Tools list - Simplified AI tools
tools = [
    get_current_date,
    get_all_sessions_data,
    parse_student_request,
    check_existing_session,
    create_new_session,
    update_existing_session,
    parse_teacher_availability,
    set_teacher_availability
]

# Create the agent with proper LangGraph syntax
agent = create_react_agent(llm, tools, state_modifier=system_prompt)

# Create the graph
class SessionAgentState(TypedDict):
    messages: List[dict]

graph_builder = StateGraph(SessionAgentState)
graph_builder.add_node("agent", agent)
graph_builder.set_entry_point("agent")
graph = graph_builder.compile()

# Test function
if __name__ == "__main__":
    print("🧪 Testing simplified AI session agent...")
    result = run_session_agent("Student test123: I want a Python session 2-3 PM")
    print(f"Result: {result}")