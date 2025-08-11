from gotrue import model
from langchain_community.chat_models import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from typing import TypedDict, List, Optional
import json
import os
from supabase import create_client, Client
from langchain_groq import ChatGroq
from datetime import datetime, timedelta

# --- Supabase Setup ---
supabase: Client = create_client(
    "https://ipfzpnxdtackprxforqh.supabase.co", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k"
)

# --- Helper Functions ---
def parse_day_to_date(day_str: str) -> str:
    """Convert day names like 'Monday' to actual dates"""
    today = datetime.now()
    days_ahead = 0
    
    if day_str.lower() == 'monday':
        days_ahead = 0 - today.weekday()
    elif day_str.lower() == 'tuesday':
        days_ahead = 1 - today.weekday()
    elif day_str.lower() == 'wednesday':
        days_ahead = 2 - today.weekday()
    elif day_str.lower() == 'thursday':
        days_ahead = 3 - today.weekday()
    elif day_str.lower() == 'friday':
        days_ahead = 4 - today.weekday()
    elif day_str.lower() == 'saturday':
        days_ahead = 5 - today.weekday()
    elif day_str.lower() == 'sunday':
        days_ahead = 6 - today.weekday()
    
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime('%Y-%m-%d')

def convert_time_format(time_str: str) -> str:
    """Convert time formats like '2 PM' to '14:00:00'"""
    time_str = time_str.strip().upper()
    
    if 'PM' in time_str or 'AM' in time_str:
        time_part = time_str.replace('PM', '').replace('AM', '').strip()
        hour = int(time_part)
        
        if 'PM' in time_str and hour != 12:
            hour += 12
        elif 'AM' in time_str and hour == 12:
            hour = 0
            
        return f"{hour:02d}:00:00"
    
    return time_str

# --- Enhanced Tools ---
@tool
def get_all_data():
    """Fetch all data from the database tables. Call this function first to get all data."""
    try:
        students_availability = supabase.table('student_availability').select('*').execute()
        students = supabase.table('students').select('*').execute()
        session_enrollments = supabase.table('session_enrollments').select('*').execute()
        sessions = supabase.table('sessions').select('*').execute()
        teacher_availability = supabase.table('teacher_availability').select('*').execute()
        teachers = supabase.table('teachers').select('*').execute()
        
        all_data = {
            'students_availability': students_availability.data,
            'students': students.data,
            'session_enrollments': session_enrollments.data,
            'sessions': sessions.data,
            'teacher_availability': teacher_availability.data,
            'teachers': teachers.data
        }
        return json.dumps(all_data, indent=2)
    except Exception as e:
        return f"Error fetching data: {e}"

@tool
def create_complete_session_workflow(input: str) -> str:
    """Complete workflow: Create session and enroll student. Input: JSON with student_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        subject = data["subject"]
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Convert time formats if needed
        start_time = convert_time_format(start_time)
        end_time = convert_time_format(end_time)
        
        # First, insert student availability
        student_availability_data = {
            "student_id": student_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "subject": subject
        }
        
        supabase.table("student_availability").insert(student_availability_data).execute()
        
        # Find available teacher (for now, use the existing teacher)
        teacher_id = "46a3bfcd-2d45-417c-b578-b4ac0f1c577c"  # From your data
        
        # Create session
        session_data = {
            "teacher_id": teacher_id,
            "subject": subject,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "meet_link": f"https://meet.google.com/{subject.lower()}-{date}",
            "status": "active",
            "total_students": 1
        }
        
        session_response = supabase.table("sessions").insert(session_data).execute()
        session_id = session_response.data[0]["id"]
        
        # Enroll student in session
        enrollment_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        
        enrollment_response = supabase.table("session_enrollments").insert(enrollment_data).execute()
        
        # Update student availability with session_id
        supabase.table("student_availability").update({"session_id": session_id}).eq("student_id", student_id).eq("date", date).execute()
        
        return f"✅ Successfully created session and enrolled student!\nSession ID: {session_id}\nSubject: {subject}\nDate: {date}\nTime: {start_time} - {end_time}\nStudent enrolled: {student_id}"
        
    except Exception as e:
        return f"Error in workflow: {e}"

@tool
def find_and_join_existing_session(input: str) -> str:
    """Find existing session for subject and enroll student. Input: JSON with student_id, subject, preferred_date, preferred_start_time, preferred_end_time."""
    try:
        data = json.loads(input)
        student_id ="1a05236f-574f-447c-841b-27fcc1813954"
        subject = data["subject"]
        
        # Find existing sessions for this subject
        existing_sessions = supabase.table("sessions").select("*").eq("subject", subject).eq("status", "active").execute()
        
        if not existing_sessions.data:
            return f"No existing sessions found for {subject}. Need to create new session."
        
        # For now, join the first available session
        session = existing_sessions.data[0]
        session_id = session["id"]
        
        # Check if student is already enrolled
        existing_enrollment = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
        
        if existing_enrollment.data:
            return f"Student {student_id} is already enrolled in session {session_id}"
        
        # Enroll student
        enrollment_data = {
            "session_id": session_id,
            "student_id": student_id
        }
        
        supabase.table("session_enrollments").insert(enrollment_data).execute()
        
        # Update total students count
        current_enrollments = supabase.table("session_enrollments").select("*").eq("session_id", session_id).execute()
        total_students = len(current_enrollments.data)
        
        supabase.table("sessions").update({"total_students": total_students}).eq("id", session_id).execute()
        
        return f"✅ Successfully enrolled student {student_id} in existing session!\nSession ID: {session_id}\nSubject: {session['subject']}\nDate: {session['date']}\nTime: {session['start_time']} - {session['end_time']}\nTotal students: {total_students}"
        
    except Exception as e:
        return f"Error joining session: {e}"

# --- Updated Tool List ---
tools = [
    get_all_data,
    create_complete_session_workflow,
    find_and_join_existing_session
]

# --- System Prompt ---
system_prompt = """
**Session Scheduling Agent**

You are an intelligent session scheduling agent. Your job is to create tutoring sessions or enroll students in existing ones.

**Your Process:**
1. **ALWAYS start with get_all_data()** to understand current state
2. **Analyze the request** to determine if student wants:
   - New session for a subject
   - Join existing session

**For NEW sessions (first student for a subject):**
- Use create_complete_session_workflow()
- Provide: student_id, subject, date, start_time, end_time
- This handles everything: student availability, session creation, and enrollment

**For JOINING existing sessions:**
- Use find_and_join_existing_session() 
- This finds existing sessions for the subject and enrolls the student
-find out the most optimal time for both students and teachers
if teacher says 12-1 1st student says 11-2 and 3rd says 2-3 then finnd most optimal and mots effective time for all

**Input Processing:**
- Convert day names (Monday, Tuesday) to proper dates
- Convert time formats (2 PM, 5 PM) to 24-hour format
- Handle various date/time formats automatically

**Important Notes:**
- Sessions must be at least 1 hour long
- Always check if sessions already exist for the subject before creating new ones
- Provide clear feedback about what was created/updated
- If there are conflicts, suggest alternative times

Be helpful and provide clear status updates!

for example :
teacher time is 12-4
student 1 time is 11-2
student 2 time is 2-3
student 3 time is 2-3
then the most optimal time is 2-3

this is the example but you should decide the most optimal time for all student and teacher but go with majority we have availibities right
so the higher the majority the better the time make sure that we should conduct the session where max number of students are there

Also create session with broad  subject like python,javascript
suppose user says i am available for flask session then you should create a session with subject python and enroll the student in that session

what i have been observerd is that suppose for first student the session form 1-2 but the next three student came and say that 11-1 then timing must get changed to 11-1

"""

# --- LangGraph Setup ---
class AgentState(TypedDict):
    messages: List[dict]
    next: Optional[str]

llm = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0,
    groq_api_key=os.getenv("groq_api_key"),
)

agent_node = create_react_agent(model=llm, tools=tools, prompt=system_prompt)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.set_entry_point("agent")

graph = graph_builder.compile()

# --- Enhanced Usage Function ---
def run_session_agent(user_input: str):
    """Run the session creation agent with user input."""
    try:
        response = graph.invoke({
            "messages": [{"role": "user", "content": user_input}]
        })
        
        # Extract the final AI message
        final_message = response["messages"][-1]
        return final_message.content if hasattr(final_message, 'content') else str(final_message)
        
    except Exception as e:
        return f"Error running agent: {e}"

# --- Test Examples ---
if __name__ == "__main__":
    print("🤖 Session Scheduling Agent Ready!")
    print("-" * 50)
    
    # Test 1: Create new session
    print("Test 1: Creating new session...")
    test1 = "I am available on monday at 11pm to 1am for flask session"
    result1 = run_session_agent(test1)
    print("Result:", result1)
    print("-" * 50)
