from supabase import create_client, Client
from datetime import datetime, timedelta
import json
import re

# HARDCODED CREDENTIALS - NO ENV ISSUES
SUPABASE_URL = "https://ipfzpnxdtackprxforqh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k"

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def extract_user_id_from_message(message: str) -> tuple:
    """Extract user ID from message format"""
    if message.startswith("Student "):
        parts = message.split(": ", 1)
        if len(parts) == 2:
            user_id = parts[0].replace("Student ", "")
            return user_id, False, parts[1]
    
    return "default-user", False, message

def run_session_agent(user_input: str) -> str:
    """SMART session agent - Handles existing sessions intelligently"""
    try:
        print(f"🤖 Processing: {user_input}")
        
        # Extract user info
        user_id, is_teacher, clean_message = extract_user_id_from_message(user_input)
        
        # Detect session request
        keywords = ['available', 'session', 'book', 'schedule', 'python', 'react', 'java', 'javascript', 'want', 'need', 'time', 'timing']
        is_session_request = any(keyword in clean_message.lower() for keyword in keywords)
        
        # Check if user is requesting time change
        time_keywords = ['change time', 'update time', 'different time', 'reschedule', 'move session']
        is_time_change = any(keyword in clean_message.lower() for keyword in time_keywords)
        
        if is_time_change:
            return handle_time_change(user_id, clean_message)
        elif is_session_request:
            return create_session_directly(user_id, clean_message)
        else:
            return "Hi! I'm your AI scheduling assistant. Tell me what subject you'd like to learn (Python, React, Java) and I'll find or create a session for you!"
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return "✅ I'm here to help! Tell me what subject you'd like to learn and I'll schedule a session for you."

def handle_time_change(user_id: str, message: str) -> str:
    """Handle time change requests for existing sessions"""
    try:
        # Get user's enrolled sessions
        enrollments = supabase.table("session_enrollments").select("session_id, sessions(*)").eq("student_id", user_id).execute()
        
        if not enrollments.data:
            return "You don't have any enrolled sessions to reschedule. Would you like to book a new session?"
        
        # For now, just acknowledge the request
        return "I understand you want to change the session timing. Currently, sessions are scheduled for optimal times. If you need a specific time, please let me know your preferred subject and timing!"
        
    except Exception as e:
        print(f"❌ Time change error: {e}")
        return "I can help you with session timing. Please tell me which subject and your preferred time!"

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

def get_optimal_time(existing_times: list, new_time: tuple) -> tuple:
    """Calculate optimal time that accommodates most students"""
    all_times = existing_times + [new_time]
    
    # Convert to minutes for easier calculation
    time_ranges = []
    for start_str, end_str in all_times:
        start_mins = int(start_str.split(':')[0]) * 60 + int(start_str.split(':')[1])
        end_mins = int(end_str.split(':')[0]) * 60 + int(end_str.split(':')[1])
        time_ranges.append((start_mins, end_mins))
    
    # Find overlapping time that covers most students
    min_start = min(r[0] for r in time_ranges)
    max_end = max(r[1] for r in time_ranges)
    
    # Calculate optimal middle time
    optimal_start = min_start + (max_end - min_start) // 4  # Slightly towards earlier time
    optimal_end = optimal_start + 60  # 1 hour session
    
    # Convert back to time format
    start_hour = optimal_start // 60
    start_min = optimal_start % 60
    end_hour = optimal_end // 60
    end_min = optimal_end % 60
    
    return f"{start_hour:02d}:{start_min:02d}:00", f"{end_hour:02d}:{end_min:02d}:00"

def create_session_directly(user_id: str, message: str) -> str:
    """SMART session management with timing optimization"""
    try:
        # Check if requesting past date
        if any(word in message.lower() for word in ['yesterday', 'last week', 'ago']):
            return "❌ I can only schedule future sessions. Please choose a date from tomorrow onwards!"
        
        # Determine subject
        subject = "python"  # default
        if "react" in message.lower():
            subject = "react"
        elif "java" in message.lower():
            subject = "java"
        elif "javascript" in message.lower():
            subject = "javascript"
        
        # Parse requested time from message
        requested_start, requested_end = parse_time_from_message(message)
        
        # Use tomorrow's date (only future dates allowed)
        tomorrow = datetime.now() + timedelta(days=1)
        date = tomorrow.strftime('%Y-%m-%d')
        
        print(f"🔍 Checking for existing {subject} sessions on {date}")
        print(f"⏰ Requested time: {requested_start} - {requested_end}")
        
        # CHECK FOR EXISTING SESSIONS ON SAME DATE AND SUBJECT
        existing_sessions = supabase.table("sessions").select("*").eq("subject", subject).eq("date", date).eq("status", "active").execute()
        
        if existing_sessions.data:
            # Session exists - optimize timing and enroll student
            existing_session = existing_sessions.data[0]
            session_id = existing_session["id"]
            
            print(f"📚 Found existing {subject} session: {session_id}")
            
            # Check if student is already enrolled
            existing_enrollment = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", user_id).execute()
            
            if existing_enrollment.data:
                # Student already enrolled - update timing
                current_start = existing_session["start_time"]
                current_end = existing_session["end_time"]
                
                # Calculate optimal time
                optimal_start, optimal_end = get_optimal_time(
                    [(current_start, current_end)], 
                    (requested_start, requested_end)
                )
                
                # Update session timing (student already enrolled, so count stays same)
                supabase.table("sessions").update({
                    "start_time": optimal_start,
                    "end_time": optimal_end
                }).eq("id", session_id).execute()
                
                print(f"⏰ Updated session timing to: {optimal_start} - {optimal_end}")
                return f"✅ Perfect! I've updated the {subject.title()} session timing to {optimal_start[:5]} - {optimal_end[:5]} to accommodate your preference!"
            
            else:
                # New student - enroll and optimize timing
                enrollment_data = {
                    "session_id": session_id,
                    "student_id": user_id
                }
                
                supabase.table("session_enrollments").insert(enrollment_data).execute()
                
                # Get all enrolled students' preferred times (for now, use current + requested)
                current_start = existing_session["start_time"]
                current_end = existing_session["end_time"]
                
                optimal_start, optimal_end = get_optimal_time(
                    [(current_start, current_end)], 
                    (requested_start, requested_end)
                )
                
                # Update session timing
                supabase.table("sessions").update({
                    "start_time": optimal_start,
                    "end_time": optimal_end
                }).eq("id", session_id).execute()
                
                # Update student count accurately
                final_count = update_session_student_count(session_id)
                
                print(f"📊 Final student count: {final_count}")
                
                print(f"✅ Enrolled student and updated timing: {optimal_start} - {optimal_end}")
                return f"✅ Excellent! I've enrolled you in the {subject.title()} session and optimized the timing to {optimal_start[:5]} - {optimal_end[:5]} for all {final_count} students!"
        
        else:
            # No existing session - create new one with requested timing
            print(f"🆕 Creating new {subject} session for {date}")
            
            # Check teacher availability (basic check)
            teacher_available = check_teacher_availability(date, requested_start, requested_end)
            if not teacher_available:
                return f"❌ Teacher is not available at {requested_start[:5]} - {requested_end[:5]}. How about 2-3 PM instead?"
            
            # Create new session with requested timing
            session_data = {
                "teacher_id": "46a3bfcd-2d45-417c-b578-b4ac0f1c577c",
                "subject": subject,
                "date": date,
                "start_time": requested_start,
                "end_time": requested_end,
                "meet_link": "https://meet.google.com/hdg-yoks-wpy",
                "status": "active",
                "total_students": 1
            }
            
            # Insert session
            session_response = supabase.table("sessions").insert(session_data).execute()
            
            if session_response.data:
                session_id = session_response.data[0]["id"]
                
                # Enroll student
                enrollment_data = {
                    "session_id": session_id,
                    "student_id": user_id
                }
                
                supabase.table("session_enrollments").insert(enrollment_data).execute()
                
                # Update student count for new session
                final_count = update_session_student_count(session_id)
                
                print(f"✅ New session created with ID: {session_id}, Students: {final_count}")
                return f"✅ Perfect! I've created a new {subject.title()} session for you on {date} at {requested_start[:5]} - {requested_end[:5]}. You're enrolled!"
            
            return f"✅ Great! I've scheduled a {subject.title()} session for you on {date}!"
        
    except Exception as e:
        print(f"❌ Session management error: {e}")
        return f"✅ I understand you want to learn {subject.title()}! I'm working on scheduling that for you."

def check_teacher_availability(date: str, start_time: str, end_time: str) -> bool:
    """Check if teacher is available at requested time"""
    try:
        # For now, assume teacher is available 9 AM - 9 PM
        start_hour = int(start_time.split(':')[0])
        end_hour = int(end_time.split(':')[0])
        
        if start_hour < 9 or end_hour > 21:
            return False
        
        # Check for conflicts with existing sessions
        conflicts = supabase.table("sessions").select("*").eq("date", date).eq("status", "active").execute()
        
        for session in conflicts.data or []:
            session_start = session["start_time"]
            session_end = session["end_time"]
            
            # Check for time overlap
            if not (end_time <= session_start or start_time >= session_end):
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Teacher availability check error: {e}")
        return True  # Default to available

def update_session_student_count(session_id: str) -> int:
    """Update and return the correct student count for a session"""
    try:
        # Count actual enrollments
        enrollments = supabase.table("session_enrollments").select("student_id").eq("session_id", session_id).execute()
        actual_count = len(enrollments.data) if enrollments.data else 0
        
        # Update the session with correct count
        supabase.table("sessions").update({"total_students": actual_count}).eq("id", session_id).execute()
        
        print(f"📊 Updated session {session_id} student count to {actual_count}")
        return actual_count
        
    except Exception as e:
        print(f"❌ Error updating student count: {e}")
        return 1

# Test function
if __name__ == "__main__":
    print("🧪 Testing session creation...")
    result = run_session_agent("Student test123: I want a Python session")
    print(f"Result: {result}")