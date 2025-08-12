from gotrue import model
from langchain_community.chat_models import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langchain.tools import tool
from typing import TypedDict, List, Optional
import json
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from supabase import create_client, Client
from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta



# --- Supabase Setup ---
supabase: Client = create_client(
    os.getenv("SUPABASE_URL", "your_supabase_url_here"), 
    os.getenv("SUPABASE_KEY", "your_supabase_key_here")
)

# --- Helper Functions ---
def extract_user_id_from_message(message: str) -> tuple:
    """Extract user ID and role from message format 'Teacher/Student user_id: message'"""
    if message.startswith("Teacher "):
        parts = message.split(": ", 1)
        if len(parts) == 2:
            user_id = parts[0].replace("Teacher ", "")
            return user_id, True, parts[1]  # user_id, is_teacher, clean_message
    elif message.startswith("Student "):
        parts = message.split(": ", 1)
        if len(parts) == 2:
            user_id = parts[0].replace("Student ", "")
            return user_id, False, parts[1]  # user_id, is_teacher, clean_message
    
    return "1a05236f-574f-447c-841b-27fcc1813954", False, message  # Default fallback

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

def time_to_minutes(time_str: str) -> int:
    """Convert time string to minutes since midnight"""
    parts = time_str.split(':')
    return int(parts[0]) * 60 + int(parts[1])

def minutes_to_time(minutes: int) -> str:
    """Convert minutes since midnight to time string"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}:00"

def get_user_info(user_id: str, is_teacher: bool) -> dict:
    """Get user information from the correct table"""
    try:
        table = 'teachers' if is_teacher else 'students'
        response = supabase.table(table).select('*').eq('user_id', user_id).execute()
        
        if response.data:
            user_data = response.data[0]
            return {
                'user_id': user_data.get('user_id', user_id),
                'name': user_data.get('name', f"{'Teacher' if is_teacher else 'Student'} {user_id[:8]}"),
                'id': user_data.get('id', user_id)  # The table's primary key
            }
        else:
            # If not found, return basic info without trying to insert
            return {
                'user_id': user_id,
                'name': f"{'Teacher' if is_teacher else 'Student'} {user_id[:8]}",
                'id': user_id
            }
            
    except Exception as e:
        print(f"Error getting user info: {e}")
        return {
            'user_id': user_id,
            'name': f"{'Teacher' if is_teacher else 'Student'} {user_id[:8]}",
            'id': user_id
        }

def map_subject_to_broad_category(subject: str) -> str:
    """Map specific topics to broad subjects for better session grouping"""
    subject_lower = subject.lower().strip()
    
    # Python-related topics
    if any(keyword in subject_lower for keyword in ['flask', 'django', 'fastapi', 'pandas', 'numpy', 'python']):
        return 'python'
    
    # React-related topics
    elif any(keyword in subject_lower for keyword in ['react', 'react hook', 'react hooks', 'jsx']):
        return 'react'
    
    # JavaScript-related topics  
    elif any(keyword in subject_lower for keyword in ['javascript', 'js', 'node', 'express', 'vue', 'angular']):
        return 'javascript'
    
    # Java-related topics
    elif any(keyword in subject_lower for keyword in ['java', 'spring', 'hibernate']):
        return 'java'
    
    # Web development
    elif any(keyword in subject_lower for keyword in ['html', 'css', 'web development', 'frontend', 'backend']):
        return 'web development'
    
    # Data Science
    elif any(keyword in subject_lower for keyword in ['machine learning', 'data science', 'ai', 'ml']):
        return 'data science'
    
    # Return the original subject if no mapping found
    return subject_lower

def find_optimal_time_slot(availabilities: list) -> dict:
    """Find the optimal time slot that accommodates maximum students with smart overlap calculation"""
    if not availabilities:
        return {"start_time": "12:00:00", "end_time": "13:00:00", "student_count": 0, "students": [], "recommendation": "No availabilities provided"}
    
    print(f"🔍 Finding optimal time for {len(availabilities)} students")
    
    # Convert all times to minutes for easier calculation
    time_slots = []
    for avail in availabilities:
        start_mins = time_to_minutes(avail["start_time"])
        end_mins = time_to_minutes(avail["end_time"])
        time_slots.append({
            "student_id": avail["student_id"],
            "start": start_mins,
            "end": end_mins,
            "duration": end_mins - start_mins
        })
        print(f"  Student {avail['student_id']}: {start_mins//60}:{start_mins%60:02d} - {end_mins//60}:{end_mins%60:02d}")
    
    # Find the best overlapping time that accommodates most students
    best_slot = {"start": 0, "end": 0, "count": 0, "students": []}
    
    # Try different 1-hour windows to find maximum overlap
    for start_hour in range(6, 22):  # 6 AM to 10 PM
        for start_min in [0, 30]:  # Every 30 minutes
            window_start = start_hour * 60 + start_min
            window_end = window_start + 60  # 1 hour window
            
            # Count how many students can attend this window
            attending_students = []
            for slot in time_slots:
                # Check if student is available during this entire window
                if slot["start"] <= window_start and slot["end"] >= window_end:
                    attending_students.append(slot["student_id"])
            
            if len(attending_students) > best_slot["count"]:
                best_slot = {
                    "start": window_start,
                    "end": window_end,
                    "count": len(attending_students),
                    "students": attending_students
                }
                print(f"  Better slot found: {start_hour}:{start_min:02d} - {(window_end//60)}:{(window_end%60):02d} ({len(attending_students)} students)")
    
    # If no perfect overlap found, find the best compromise time
    if best_slot["count"] <= 1:
        print("  No perfect overlap found, finding best compromise...")
        
        # Find the time range that covers most students
        all_starts = [slot["start"] for slot in time_slots]
        all_ends = [slot["end"] for slot in time_slots]
        
        # Try the middle ground - average of all times
        avg_start = sum(all_starts) // len(all_starts)
        avg_end = sum(all_ends) // len(all_ends)
        
        # Ensure at least 1 hour duration
        if avg_end - avg_start < 60:
            avg_end = avg_start + 60
        
        # Round to nearest 30 minutes for cleaner times
        avg_start = (avg_start // 30) * 30
        avg_end = (avg_end // 30) * 30
        
        # Count how many students can attend this compromise time
        compromise_students = []
        for slot in time_slots:
            # Check if there's any overlap with the compromise time
            if not (avg_end <= slot["start"] or avg_start >= slot["end"]):
                compromise_students.append(slot["student_id"])
        
        best_slot = {
            "start": avg_start,
            "end": avg_end,
            "count": len(compromise_students),
            "students": compromise_students
        }
        
        print(f"  Compromise time: {avg_start//60}:{avg_start%60:02d} - {avg_end//60}:{avg_end%60:02d} ({len(compromise_students)} students)")
    
    optimal_start = minutes_to_time(best_slot["start"])
    optimal_end = minutes_to_time(best_slot["end"])
    
    print(f"  🎯 Optimal time: {optimal_start} - {optimal_end} ({best_slot['count']} students)")
    
    return {
        "start_time": optimal_start,
        "end_time": optimal_end,
        "student_count": best_slot["count"],
        "students": best_slot["students"],
        "recommendation": f"Optimal time {optimal_start}-{optimal_end} accommodates {best_slot['count']} students"
    }

# --- Enhanced Tools ---
@tool
def get_all_data():
    """Get ALL database data for AI to make smart decisions. This gives complete context."""
    try:
        print("🔄 Getting all data for AI...")
        
        # Get ALL data from ALL tables
        students_availability = supabase.table('student_availability').select('*').execute()
        students = supabase.table('students').select('*').execute()
        session_enrollments = supabase.table('session_enrollments').select('*').execute()
        sessions = supabase.table('sessions').select('*').execute()
        teacher_availability = supabase.table('teacher_availability').select('*').execute()
        teachers = supabase.table('teachers').select('*').execute()
        
        # Give AI EVERYTHING to make smart decisions
        complete_data = {
            'current_sessions': sessions.data,
            'student_enrollments': session_enrollments.data,
            'all_students': students.data,
            'all_teachers': teachers.data,
            'student_availability_history': students_availability.data,
            'teacher_availability': teacher_availability.data,
            'summary': {
                'total_active_sessions': len([s for s in sessions.data if s.get('status') == 'active']),
                'total_students': len(students.data),
                'total_teachers': len(teachers.data),
                'total_enrollments': len(session_enrollments.data)
            }
        }
        
        print(f"✅ Complete data loaded for AI decision making")
        return json.dumps(complete_data, indent=2, default=str)
    except Exception as e:
        return f"Database connection issue. Please try again."

@tool
def create_complete_session_workflow(input: str) -> str:
    """Complete workflow: Create session and enroll student. Input: JSON with student_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]  # This should always be provided now
        original_subject = data["subject"]
        broad_subject = map_subject_to_broad_category(original_subject)
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
            "subject": broad_subject
        }
        
        supabase.table("student_availability").insert(student_availability_data).execute()
        
        # Use the single teacher in the system
        teacher_response = supabase.table('teachers').select('user_id').limit(1).execute()
        if teacher_response.data:
            teacher_id = teacher_response.data[0]['user_id']
        else:
            teacher_id = "46a3bfcd-2d45-417c-b578-b4ac0f1c577c"  # Fallback
        
        # Create session
        session_data = {
            "teacher_id": teacher_id,
            "subject": broad_subject,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "meet_link": f"https://meet.google.com/{broad_subject.lower()}-{date}",
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
        
        return f"✅ Session created for {broad_subject} on {date} at {start_time}-{end_time}"
        
    except Exception as e:
        return f"Error in workflow: {e}"

@tool
def check_teacher_availability(input: str) -> str:
    """Check if teacher is available for the requested time slot. Input: JSON with date, start_time, end_time."""
    try:
        data = json.loads(input)
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Convert time formats if needed
        start_time = convert_time_format(start_time)
        end_time = convert_time_format(end_time)
        
        # Get teacher availability for this date
        teacher_availability = supabase.table("teacher_availability").select("*").eq("date", date).execute()
        
        available_slots = []
        is_available = False
        
        if teacher_availability.data:
            for slot in teacher_availability.data:
                slot_start = time_to_minutes(slot["start_time"])
                slot_end = time_to_minutes(slot["end_time"])
                request_start = time_to_minutes(start_time)
                request_end = time_to_minutes(end_time)
                
                # Check if requested time fits within teacher's availability
                if slot_start <= request_start and slot_end >= request_end:
                    is_available = True
                
                available_slots.append(f"{slot['start_time']}-{slot['end_time']} for {slot['subject']}")
        
        return json.dumps({
            "is_available": is_available,
            "requested_time": f"{start_time}-{end_time}",
            "date": date,
            "available_slots": available_slots,
            "message": "Teacher available" if is_available else f"Teacher not available at {start_time}-{end_time}. Available: {', '.join(available_slots)}"
        })
        
    except Exception as e:
        return f"Error checking teacher availability: {e}"

@tool
def find_existing_session_for_subject(input: str) -> str:
    """Find existing session for the same subject and date. Input: JSON with subject, date."""
    try:
        data = json.loads(input)
        subject = data["subject"]
        date = data["date"]
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Map subject to broad category
        broad_subject = map_subject_to_broad_category(subject)
        
        # Find existing sessions for this subject on this date
        existing_sessions = supabase.table("sessions").select("*").eq("subject", broad_subject).eq("date", date).eq("status", "active").execute()
        
        if existing_sessions.data:
            session = existing_sessions.data[0]  # Get the first (should be only one)
            
            # Get all students enrolled in this session
            enrollments = supabase.table("session_enrollments").select("student_id").eq("session_id", session["id"]).execute()
            enrolled_students = [e["student_id"] for e in enrollments.data] if enrollments.data else []
            
            return json.dumps({
                "session_exists": True,
                "session_id": session["id"],
                "current_time": f"{session['start_time']} - {session['end_time']}",
                "enrolled_students": enrolled_students,
                "total_students": len(enrolled_students),
                "session_details": session
            })
        else:
            return json.dumps({
                "session_exists": False,
                "message": f"No existing session found for {broad_subject} on {date}"
            })
            
    except Exception as e:
        return f"Error finding existing session: {e}"

@tool
def analyze_optimal_session_time(input: str) -> str:
    """Analyze all student availabilities for a subject and determine optimal session time. Input: JSON with subject, date, new_student_availability."""
    try:
        data = json.loads(input)
        original_subject = data["subject"]
        broad_subject = map_subject_to_broad_category(original_subject)
        date = data["date"]
        new_student_id = data["student_id"]
        new_start_time = data["start_time"]
        new_end_time = data["end_time"]
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Convert time formats if needed
        new_start_time = convert_time_format(new_start_time)
        new_end_time = convert_time_format(new_end_time)
        
        # Get all existing sessions for this broad subject on this date
        existing_sessions = supabase.table("sessions").select("*").eq("subject", broad_subject).eq("date", date).eq("status", "active").execute()
        
        # Get all student availabilities for this broad subject on this date
        student_availabilities = supabase.table("student_availability").select("*").eq("subject", broad_subject).eq("date", date).execute()
        
        # Add the new student's availability to analysis
        all_availabilities = student_availabilities.data + [{
            "student_id": new_student_id,
            "start_time": new_start_time,
            "end_time": new_end_time,
            "subject": broad_subject,
            "date": date
        }]
        
        # Find optimal time slot that accommodates maximum students
        optimal_analysis = find_optimal_time_slot(all_availabilities)
        
        return json.dumps({
            "original_subject": original_subject,
            "broad_subject": broad_subject,
            "optimal_start_time": optimal_analysis["start_time"],
            "optimal_end_time": optimal_analysis["end_time"],
            "student_count": optimal_analysis["student_count"],
            "participating_students": optimal_analysis["students"],
            "existing_sessions": existing_sessions.data,
            "recommendation": optimal_analysis["recommendation"],
            "date": date
        })
        
    except Exception as e:
        return f"Error analyzing optimal time: {e}"

@tool
def update_existing_session_time(input: str) -> str:
    """Update existing session time to accommodate more students. Input: JSON with session_id, new_start_time, new_end_time, reason."""
    try:
        data = json.loads(input)
        session_id = data["session_id"]
        new_start_time = data["new_start_time"]
        new_end_time = data["new_end_time"]
        reason = data.get("reason", "Optimizing for more students")
        
        # Update the session
        update_response = supabase.table("sessions").update({
            "start_time": new_start_time,
            "end_time": new_end_time
        }).eq("id", session_id).execute()
        
        if update_response.data:
            return f"✅ Session updated to {new_start_time}-{new_end_time}"
        else:
            return f"❌ Failed to update session"
            
    except Exception as e:
        return f"Error updating session: {e}"

@tool
def enroll_student_in_session(input: str) -> str:
    """Enroll a student in a specific session. Input: JSON with session_id, student_id."""
    try:
        data = json.loads(input)
        session_id = data["session_id"]
        student_id = data["student_id"]
        
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
        
        # Add student availability record
        session_data = supabase.table("sessions").select("*").eq("id", session_id).execute().data[0]
        supabase.table("student_availability").insert({
            "student_id": student_id,
            "date": session_data["date"],
            "start_time": session_data["start_time"],
            "end_time": session_data["end_time"],
            "subject": session_data["subject"],
            "session_id": session_id
        }).execute()
        
        return f"✅ Enrolled in {session_data['subject']} session ({total_students} students total)"
        
    except Exception as e:
        return f"Error enrolling student: {e}"

@tool
def validate_timing_request(input: str) -> str:
    """Validate if the requested timing is reasonable and provide helpful feedback. Input: JSON with date, start_time, end_time, subject."""
    try:
        data = json.loads(input)
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        subject = data["subject"]
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Convert time formats if needed
        start_time = convert_time_format(start_time)
        end_time = convert_time_format(end_time)
        
        start_mins = time_to_minutes(start_time)
        end_mins = time_to_minutes(end_time)
        duration_mins = end_mins - start_mins
        
        # Check for odd timings and provide helpful responses
        issues = []
        suggestions = []
        
        # Check if timing is too late (after 10 PM) or too early (before 6 AM)
        if start_mins >= 22 * 60:  # After 10 PM
            issues.append("very late timing (after 10 PM)")
            suggestions.append("Consider scheduling between 9 AM - 9 PM for better availability")
            
        if start_mins < 6 * 60:  # Before 6 AM
            issues.append("very early timing (before 6 AM)")
            suggestions.append("Most sessions are scheduled between 9 AM - 9 PM")
        
        # Check if duration is too short or too long
        if duration_mins < 30:
            issues.append("session too short (less than 30 minutes)")
            suggestions.append("Sessions should be at least 1 hour for effective learning")
            
        if duration_mins > 4 * 60:  # More than 4 hours
            issues.append("session too long (more than 4 hours)")
            suggestions.append("Consider breaking into multiple shorter sessions")
        
        # Check if it's a weekend late night
        target_date = datetime.strptime(date, '%Y-%m-%d')
        if target_date.weekday() >= 5 and start_mins >= 21 * 60:  # Weekend after 9 PM
            issues.append("weekend late night timing")
            suggestions.append("Weekend evening sessions have lower teacher availability")
        
        # Get existing sessions to check popular times
        existing_sessions = supabase.table("sessions").select("start_time, end_time").eq("subject", map_subject_to_broad_category(subject)).eq("status", "active").execute()
        
        popular_times = []
        if existing_sessions.data:
            time_counts = {}
            for session in existing_sessions.data:
                time_key = f"{session['start_time']}-{session['end_time']}"
                time_counts[time_key] = time_counts.get(time_key, 0) + 1
            
            # Get top 3 popular times
            popular_times = sorted(time_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return json.dumps({
            "is_reasonable": len(issues) == 0,
            "issues": issues,
            "suggestions": suggestions,
            "popular_times": [time for time, count in popular_times],
            "duration_minutes": duration_mins,
            "timing_category": get_timing_category(start_mins),
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        })
        
    except Exception as e:
        return f"Error validating timing: {e}"

def get_timing_category(start_mins: int) -> str:
    """Categorize timing for better feedback"""
    if start_mins < 6 * 60:
        return "very_early"
    elif start_mins < 9 * 60:
        return "early_morning"
    elif start_mins < 12 * 60:
        return "morning"
    elif start_mins < 17 * 60:
        return "afternoon"
    elif start_mins < 21 * 60:
        return "evening"
    else:
        return "late_night"

@tool
def check_session_conflicts(input: str) -> str:
    """Check for session conflicts before creating or updating. Input: JSON with date, start_time, end_time, subject, exclude_session_id (optional)."""
    try:
        data = json.loads(input)
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        subject = data["subject"]
        exclude_session_id = data.get("exclude_session_id", None)
        
        # Convert day names to dates if needed
        if not date[0].isdigit():
            date = parse_day_to_date(date)
        
        # Convert time formats if needed
        start_time = convert_time_format(start_time)
        end_time = convert_time_format(end_time)
        
        # Check for overlapping sessions
        query = supabase.table("sessions").select("*").eq("date", date).eq("status", "active")
        
        if exclude_session_id:
            query = query.neq("id", exclude_session_id)
            
        existing_sessions = query.execute()
        
        conflicts = []
        for session in existing_sessions.data:
            session_start = time_to_minutes(session["start_time"])
            session_end = time_to_minutes(session["end_time"])
            new_start = time_to_minutes(start_time)
            new_end = time_to_minutes(end_time)
            
            # Check for overlap
            if not (new_end <= session_start or new_start >= session_end):
                conflicts.append({
                    "session_id": session["id"],
                    "subject": session["subject"],
                    "time": f"{session['start_time']} - {session['end_time']}",
                    "students": session["total_students"]
                })
        
        return json.dumps({
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "proposed_time": f"{start_time} - {end_time}",
            "date": date,
            "subject": subject
        })
        
    except Exception as e:
        return f"Error checking conflicts: {e}"

@tool
def create_teacher_availability(input: str) -> str:
    """Create teacher availability slot. Input: JSON with teacher_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        teacher_id = data["teacher_id"]
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
        
        # Create teacher availability
        availability_data = {
            "teacher_id": teacher_id,
            "subject": subject,
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }
        
        supabase.table("teacher_availability").insert(availability_data).execute()
        
        return f"✅ Teacher availability created!\nSubject: {subject}\nDate: {date}\nTime: {start_time} - {end_time}"
        
    except Exception as e:
        return f"Error creating teacher availability: {e}"

@tool
def handle_session_request(input: str) -> str:
    """Handle any session request - create, join, or update sessions intelligently. Input: JSON with student_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        student_id = data.get("student_id")
        subject = data.get("subject", "").lower()
        date = data.get("date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        
        # Convert formats
        if date and not date[0].isdigit():
            date = parse_day_to_date(date)
        if start_time:
            start_time = convert_time_format(start_time)
        if end_time:
            end_time = convert_time_format(end_time)
        
        # Map subject to broad category
        broad_subject = map_subject_to_broad_category(subject)
        
        # Check if session exists for this subject on this date
        existing_sessions = supabase.table("sessions").select("*").eq("subject", broad_subject).eq("date", date).eq("status", "active").execute()
        
        if existing_sessions.data:
            # Session exists - join or optimize
            session = existing_sessions.data[0]
            session_id = session["id"]
            
            # Check if student already enrolled
            existing_enrollment = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
            
            if existing_enrollment.data:
                return "You're already enrolled in this session!"
            
            # Get all students in this session to find optimal time
            all_enrollments = supabase.table("session_enrollments").select("*").eq("session_id", session_id).execute()
            all_availabilities = supabase.table("student_availability").select("*").eq("subject", broad_subject).eq("date", date).execute()
            
            # Add new student's availability
            new_availability = {
                "student_id": student_id,
                "start_time": start_time,
                "end_time": end_time,
                "subject": broad_subject,
                "date": date
            }
            
            all_student_times = all_availabilities.data + [new_availability]
            
            # Find optimal time
            optimal_result = find_optimal_time_slot(all_student_times)
            optimal_start = optimal_result["start_time"]
            optimal_end = optimal_result["end_time"]
            
            # Update session time if different
            if optimal_start != session["start_time"] or optimal_end != session["end_time"]:
                supabase.table("sessions").update({
                    "start_time": optimal_start,
                    "end_time": optimal_end
                }).eq("id", session_id).execute()
            
            # Enroll student
            supabase.table("session_enrollments").insert({
                "session_id": session_id,
                "student_id": student_id
            }).execute()
            
            # Update student count
            total_students = len(all_enrollments.data) + 1
            supabase.table("sessions").update({"total_students": total_students}).eq("id", session_id).execute()
            
            # Save student availability
            supabase.table("student_availability").insert(new_availability).execute()
            
            return f"✅ Joined {broad_subject} session! Time: {optimal_start}-{optimal_end}"
            
        else:
            # No session exists - create new one
            teacher_response = supabase.table('teachers').select('user_id').limit(1).execute()
            teacher_id = teacher_response.data[0]['user_id'] if teacher_response.data else "46a3bfcd-2d45-417c-b578-b4ac0f1c577c"
            
            # Create session
            session_data = {
                "teacher_id": teacher_id,
                "subject": broad_subject,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "meet_link": f"https://meet.google.com/{broad_subject}-{date}",
                "status": "active",
                "total_students": 1
            }
            
            session_response = supabase.table("sessions").insert(session_data).execute()
            session_id = session_response.data[0]["id"]
            
            # Enroll student
            supabase.table("session_enrollments").insert({
                "session_id": session_id,
                "student_id": student_id
            }).execute()
            
            # Save student availability
            supabase.table("student_availability").insert({
                "student_id": student_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "subject": broad_subject,
                "session_id": session_id
            }).execute()
            
            return f"✅ Created {broad_subject} session! Time: {start_time}-{end_time}"
            
    except Exception as e:
        return "Something went wrong. Please try again with your timing and subject."

# --- Simplified Tool List ---
tools = [
    get_all_data,
    handle_session_request
]

# --- System Prompt ---
system_prompt = """
You are a friendly AI session scheduler. Help students book learning sessions.

**What you do:**
1. First call get_all_data() to see all current sessions and students
2. Then call handle_session_request() to create or join sessions

**How to respond:**
- Success: "✅ Great! You're in the Python session on Monday 2-3 PM"
- Already enrolled: "You're already signed up for that session!"
- Time issue: "That time doesn't work. How about 2-4 PM instead?"
- Keep it simple and friendly!

**Subject mapping:**
- Flask/Django → Python sessions
- React/Vue → JavaScript sessions  
- Spring → Java sessions

**Rules:**
- One session per subject per day
- If multiple students want same subject, find time that works for most
- Always be helpful and friendly
- Keep responses short and clear

**Your Process:**
1. **ALWAYS start with get_all_data()** to understand current state
2. **USER IS ALREADY AUTHENTICATED** - You will receive user context in format:
   ```
   CURRENT USER CONTEXT:
   - User ID: [actual_user_id]
   - Role: Teacher/Student
   - User Message: [actual_message]
   ```
3. **NEVER ask for user ID or student ID** - Use the provided User ID for all operations
4. **Analyze the request** intelligently using the authenticated user's ID

**For TEACHERS setting availability:**
- Use create_teacher_availability() to set their availability
- Teachers provide broad time slots (e.g., "12-4 PM for Python")
- This creates availability that students can request sessions within

**For STUDENTS requesting sessions:**
- **INTELLIGENT DECISION MAKING PROCESS:**
  1. Use analyze_optimal_session_time() to find the best time slot
  2. Check if existing sessions can be optimized
  3. Make smart decisions about creating new vs updating existing sessions

**OPTIMIZATION LOGIC (CRITICAL):**
- **Scenario 1**: Teacher available 12-4 PM, Student 1 requests 12-1 PM for Flask
  → Create session 12-1 PM for Python (Flask maps to Python)
  
- **Scenario 2**: Student 2 requests 12-2 PM for Flask  
  → Analyze: Can we update existing 12-1 session to 12-2 to accommodate both students?
  → Use update_existing_session_time() if it benefits more students
  
- **Scenario 3**: Student 3 requests 1-2 PM for Flask
  → Analyze all availabilities: Student 1 (12-1), Student 2 (12-2), Student 3 (1-2)
  → Find optimal overlap: Maybe 1-2 PM accommodates Students 2&3 (majority wins)
  → Update session time accordingly

**DECISION FRAMEWORK:**
1. **Always prioritize maximum student participation**
2. **Update existing sessions** rather than creating new ones when beneficial
3. **Find overlapping time slots** that work for most students
4. **Sessions must be minimum 1 hour long**
5. **Map specific topics to broad subjects** (flask→python, react→javascript)

**Tools Usage:**
- get_all_data(): Always start with this to get FRESH up-to-date data
- validate_timing_request(): Check if timing is reasonable, provide helpful feedback for odd requests
- find_existing_session_for_subject(): CRITICAL - Check if session already exists for same subject/date
- analyze_optimal_session_time(): Get AI recommendation for best time when merging students
- update_existing_session_time(): Modify existing session timing to accommodate more students
- enroll_student_in_session(): Add student to existing session
- check_session_conflicts(): Check for conflicts before creating/updating sessions
- create_complete_session_workflow(): ONLY use when NO existing session found
- create_teacher_availability(): For teachers setting their availability

**CRITICAL RULES:**
- NEVER create duplicate sessions for same subject on same date!
- ALWAYS give SHORT responses: "✅ Session created" or "✅ Enrolled in session"
- NO explanations, NO long messages, NO reasoning details

**Response Style:**
- Keep responses SHORT and simple
- For successful enrollment: "✅ Enrolled in [subject] session"
- For session creation: "✅ Session created for [subject]"
- For session updates: "✅ Session updated"
- For odd timing: "That timing is unusual. Try 9 AM - 9 PM instead."
- NO long explanations or detailed reasoning

**MANDATORY WORKFLOW FOR STUDENT REQUESTS (NO SHORTCUTS ALLOWED):**
1. **get_all_data()** - Get FRESH up-to-date data from Supabase
2. **validate_timing_request()** - Check if timing is reasonable
3. **find_existing_session_for_subject()** - MANDATORY: Check if session exists for same subject/date

**CRITICAL DECISION LOGIC (MUST FOLLOW EXACTLY):**
- **IF SESSION EXISTS:**
  - STEP A: ALWAYS call analyze_optimal_session_time() with ALL student availabilities (existing + new)
  - STEP B: Compare optimal time with current session time
  - STEP C: If optimal time ≠ current time → MUST call update_existing_session_time() FIRST, then enroll_student_in_session()
  - STEP D: If optimal time = current time → just call enroll_student_in_session()

- **IF NO SESSION EXISTS:**
  - STEP A: Call create_complete_session_workflow() to create new session

**UNAVAILABLE SLOT RESPONSES:**
- No teacher available: "❌ No teacher available for [subject] at [time]. Available slots: [list alternatives]"
- Time conflict: "❌ That time conflicts. Available: [list free slots]"
- Outside hours: "❌ That's outside normal hours (9 AM - 9 PM). Try: [suggest 2-3 good times]"

**ABSOLUTE RULES:**
- NEVER skip analyze_optimal_session_time() when session exists
- ALWAYS update session time if optimal time is different
- ONE SESSION PER SUBJECT PER DATE

**WORKFLOW FOR TEACHER REQUESTS:**
1. **get_all_data()** - Understand current state  
2. **check_session_conflicts()** - Ensure no conflicts with teacher's availability
3. **create_teacher_availability()** - Set teacher availability

"""

# --- LangGraph Setup ---
class AgentState(TypedDict):
    messages: List[dict]
    next: Optional[str]

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
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
        # Extract user information from the message
        user_id, is_teacher, clean_message = extract_user_id_from_message(user_input)
        
        print(f"DEBUG: Extracted - User ID: {user_id}, Is Teacher: {is_teacher}, Message: {clean_message}")
        
        # Get user info from the correct table
        user_info = get_user_info(user_id, is_teacher)
        
        # Simple context for AI
        contextual_input = f"""
Student {user_info.get('name', 'User')} (ID: {user_id}) says: {clean_message}

Help them book a session! Use:
1. get_all_data() to see current sessions
2. handle_session_request() with student_id: "{user_id}" to book/join sessions

Be friendly and keep responses short!
"""
        
        response = graph.invoke({
            "messages": [{"role": "user", "content": contextual_input}]
        })
        
        # Extract the final AI message
        final_message = response["messages"][-1]
        return final_message.content if hasattr(final_message, 'content') else str(final_message)
        
    except Exception as e:
        print(f"ERROR in run_session_agent: {e}")
        return f"I understand your request. There was a technical issue, but I'm working on it. Please try again or rephrase your message."

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
