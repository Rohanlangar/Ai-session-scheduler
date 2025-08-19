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
    # Look for time patterns like "12-1pm", "2-3 PM", "1:30-2:30", "2 to 3 PM"
    time_patterns = [
        r'(\d{1,2}):?(\d{0,2})\s*-\s*(\d{1,2}):?(\d{0,2})\s*(am|pm)',
        r'(\d{1,2})\s*to\s*(\d{1,2})\s*(am|pm)',
        r'(\d{1,2})\s*(am|pm)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message.lower())
        if match:
            groups = match.groups()
            if len(groups) >= 3:  # We have start, end, and am/pm
                start_hour = int(groups[0])
                end_hour = int(groups[2]) if groups[2] else start_hour + 1
                am_pm = groups[-1]  # Last group is am/pm
                
                # Handle PM conversion
                if am_pm == 'pm' and start_hour < 12:
                    start_hour += 12
                    if end_hour <= start_hour - 12:  # end_hour is also PM
                        end_hour += 12
                elif am_pm == 'am' and start_hour == 12:
                    start_hour = 0
                    if end_hour == 12:
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
    
    # Strategy 1: Find the maximum overlap (intersection of all ranges)
    max_start = max(r[0] for r in time_ranges)  # Latest start time
    min_end = min(r[1] for r in time_ranges)    # Earliest end time
    
    print(f"  Max overlap: {max_start//60:02d}:{max_start%60:02d} - {min_end//60:02d}:{min_end%60:02d}")
    
    # If there's a valid overlap (at least 30 minutes), use it
    if min_end - max_start >= 30:
        print("✅ Found valid overlap - using intersection")
        optimal_start = f"{max_start//60:02d}:{max_start%60:02d}:00"
        optimal_end = f"{min_end//60:02d}:{min_end%60:02d}:00"
    else:
        # Strategy 2: No overlap - find the most common time range
        print("❌ No overlap found - finding best compromise")
        
        # Group similar time ranges (within 2 hours of each other)
        groups = []
        for start_mins, end_mins in time_ranges:
            placed = False
            for group in groups:
                # Check if this timing is similar to existing group (within 2 hours)
                group_avg_start = sum(r[0] for r in group) // len(group)
                if abs(start_mins - group_avg_start) <= 120:  # Within 2 hours
                    group.append((start_mins, end_mins))
                    placed = True
                    break
            
            if not placed:
                groups.append([(start_mins, end_mins)])
        
        # Find the largest group (most students with similar timing)
        largest_group = max(groups, key=len)
        print(f"  Largest group has {len(largest_group)} students")
        
        # Use average of the largest group
        group_starts = [r[0] for r in largest_group]
        group_ends = [r[1] for r in largest_group]
        
        avg_start = sum(group_starts) // len(group_starts)
        avg_end = sum(group_ends) // len(group_ends)
        
        # Ensure minimum 1 hour duration
        if avg_end - avg_start < 60:
            avg_end = avg_start + 60
        
        optimal_start = f"{avg_start//60:02d}:{avg_start%60:02d}:00"
        optimal_end = f"{avg_end//60:02d}:{avg_end%60:02d}:00"
        
        print(f"  Using largest group average: {optimal_start} - {optimal_end}")
    
    print(f"🎯 Optimal timing: {optimal_start} - {optimal_end}")
    return optimal_start, optimal_end

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
    print("✅ Anthropic LLM initialized successfully")
except Exception as e:
    print(f"⚠️ Anthropic LLM initialization failed: {e}")
    print("🔧 Using mock LLM for testing")
    llm = None

# System prompt for the agent
system_prompt = """
You are an intelligent AI session scheduler. Help students book sessions and teachers set availability.

**FOR STUDENTS (message starts with "Student"):**
1. **Call parse_student_request()** to extract subject, timing, and date from student message
2. **Use the session_date from parse_student_request result** - DO NOT use get_current_date()
3. **Call check_existing_session()** with the subject and session_date from step 1
4. **If session exists (exists=True):** 
   - First call analyze_timing_conflict() to get AI recommendation for optimal timing
   - Then call update_existing_session() to add student with AI-optimized timing
5. **If session doesn't exist (exists=False):** Call create_new_session() with session_date from step 1

**FOR TEACHERS (contextual input mentions "TEACHER"):**
1. **Call parse_teacher_availability()** to extract teacher_id, date, and timing
2. **Call set_teacher_availability()** with the parsed data
3. **NEVER call student session tools for teachers**
4. **Teachers don't need to specify subjects - they can teach any subject**
5. **ALWAYS provide a friendly response** confirming the availability was set
6. **Example responses:** 
   - "✅ Perfect! I've set your availability for Monday from 2:00 PM to 5:00 PM"
   - "✅ Great! Your availability for tomorrow 12-4 PM has been saved"

**INTELLIGENT SUBJECT MAPPING:**
- The system now uses AI to intelligently map ANY technology to broad categories
- Examples: LangChain/Streamlit/OpenAI → "python", Next.js/Gatsby → "react"
- Students can request ANY technology - the system will automatically categorize it
- Sessions are created for broad categories but can cover specific technologies within them

**CRITICAL SESSION CREATION RULES:**
- ALWAYS create sessions for MAIN SUBJECTS only (python, react, java, javascript, etc.)
- The AI will automatically map specific technologies to broad categories
- Students can ask for "LangChain session" and it will create a "python" session
- Students can ask for "Next.js session" and it will create a "react" session
- Trust the AI subject mapping - it handles new and emerging technologies

**WORKFLOW RULES:**
- If input mentions "TEACHER" → ONLY use teacher tools (parse_teacher_availability, set_teacher_availability)
- If input mentions "STUDENT" → ONLY use student tools (parse_student_request, check_existing_session, etc.)
- NEVER mix teacher and student workflows
- Teachers set availability for ANY subject - don't ask for subject clarification
- Students must specify both subject and timing
- Keep responses short and friendly

**IMPORTANT:** 
- Teachers: Use parse_teacher_availability() first, then set_teacher_availability()
- Students: Use student workflow for session booking
- ALWAYS use broad subject categories when creating sessions
- Teachers don't need to specify subjects - they can teach any subject
- If teacher message has date and time, process it immediately 
"""

def run_session_agent(user_input: str) -> str:
    """Run the session creation agent with user input."""
    try:
        # Extract user information from the message
        user_id, is_teacher_from_message, clean_message = extract_user_id_from_message(user_input)
        
        print(f"🔍 Processing - User ID: {user_id}, Message: {clean_message}")
        
        # Detect intent from message content, not just user ID
        TEACHER_ID = 'e4bcab2f-8da5-4a78-85e8-094f4d7ac308'
        is_teacher_user = (user_id == TEACHER_ID)
        
        # Check message intent - teacher availability vs student session request
        message_lower = clean_message.lower()
        teacher_keywords = ["set availability", "available from", "availability from", "my availability", "i'm available", "im available"]
        student_keywords = ["want", "need", "session", "book", "available for", "request"]
        
        # Determine if this is teacher availability or student session request
        is_teacher_intent = any(keyword in message_lower for keyword in teacher_keywords)
        is_student_intent = any(keyword in message_lower for keyword in student_keywords)
        
        # Final decision: prioritize message intent over user role
        if is_student_intent and not is_teacher_intent:
            treat_as_teacher = False
            print(f"🔍 Detected STUDENT intent from message: '{clean_message}'")
        elif is_teacher_intent:
            treat_as_teacher = True
            print(f"🔍 Detected TEACHER intent from message: '{clean_message}'")
        else:
            # Fallback to user role
            treat_as_teacher = is_teacher_user
            print(f"🔍 Using user role: {'TEACHER' if treat_as_teacher else 'STUDENT'} (user_id: {user_id})")
        
        if treat_as_teacher:
            # This is a teacher - handle availability setting
            contextual_input = f"""
Teacher {user_id} says: {clean_message}

This is a TEACHER setting availability. Teachers can teach ANY subject, so don't ask for subject clarification.
Follow teacher workflow:
1. Call parse_teacher_availability() to extract date and timing from the message
2. Call set_teacher_availability() with the parsed data
3. Do NOT call any student session tools
4. Do NOT ask for subject - teachers can teach any subject

If the message contains time information (like "12pm to 4pm" or "Friday 12-5 PM"), process it immediately.
Keep response short and friendly!
"""
        else:
            # This is a student - handle session booking
            contextual_input = f"""
Student {user_id} wants: {clean_message}

This is a STUDENT booking sessions. Follow student workflow:
1. Call parse_student_request() to get subject, timing, and date from message
2. Use the parsed date from the student request (not current date)
3. Call check_existing_session() with the parsed subject and date
4. Create new session OR update existing session with optimal timing

CRITICAL: Sessions must be created for MAIN SUBJECTS only:
- Flask/Django/FastAPI requests → create "python" session
- React/Next.js/JSX requests → create "react" session  
- Spring/Hibernate requests → create "java" session
- Node.js/Express requests → create "javascript" session

NEVER create sessions for specific subtopics or frameworks!

Keep response short and friendly!
"""
        
        if llm is None:
            # Mock response for testing when API key is invalid
            if treat_as_teacher:
                return "✅ I understand you want to set your availability! Please get a valid Anthropic API key to use the full AI features."
            else:
                return "✅ I understand you want to book a session! Please get a valid Anthropic API key to use the full AI features."
        
        # Include system prompt in messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": contextual_input}
        ]
        
        response = graph.invoke({
            "messages": messages
        })
        
        # Simple response extraction
        if "messages" in response and response["messages"]:
            final_message = response["messages"][-1]
            if hasattr(final_message, 'content'):
                return final_message.content
            elif isinstance(final_message, dict) and 'content' in final_message:
                return final_message['content']
        
        return "✅ Request processed successfully!"
        
    except Exception as e:
        print(f"❌ ERROR in run_session_agent: {e}")
        return f"I understand you want to help. Let me assist you with that!"

# === HELPER FUNCTIONS ===

def normalize_subject_with_ai(subject: str) -> str:
    """Use AI to intelligently map any subject to broad categories.
    
    This allows for flexible subject recognition including new technologies
    like LangChain, Streamlit, etc.
    """
    try:
        # Initialize Claude
        llm = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        prompt = f"""
        Map the following technology/subject to ONE of these broad categories:
        - python (for Python, Django, Flask, FastAPI, LangChain, Streamlit, pandas, etc.)
        - react (for React, Next.js, JSX, Redux, etc.)
        - vue (for Vue.js, Nuxt, Vuex, etc.)
        - java (for Java, Spring, Hibernate, etc.)
        - javascript (for Node.js, Express, vanilla JS, etc.)
        - database (for SQL, MySQL, MongoDB, PostgreSQL, etc.)
        - web (for HTML, CSS, Bootstrap, Tailwind, etc.)
        - mobile (for Android, iOS, Flutter, React Native, etc.)
        - devops (for Docker, Kubernetes, AWS, CI/CD, etc.)
        
        Subject to map: "{subject}"
        
        Return ONLY the broad category name (e.g., "python", "react", etc.). No explanation.
        """
        
        response = llm.invoke(prompt)
        mapped_subject = response.content.strip().lower()
        
        # Validate the response is one of our allowed subjects
        allowed_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops"]
        if mapped_subject in allowed_subjects:
            print(f"🤖 AI mapped '{subject}' to '{mapped_subject}'")
            return mapped_subject
        else:
            print(f"⚠️ AI returned invalid subject '{mapped_subject}', defaulting to 'python'")
            return "python"
            
    except Exception as e:
        print(f"❌ AI subject mapping failed: {e}")
        # Fallback to manual mapping
        return normalize_subject_manual(subject)

def normalize_subject_manual(subject: str) -> str:
    """Fallback manual subject mapping"""
    subject = subject.lower().strip()
    
    # Direct mapping for broad subjects
    allowed_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops"]
    if subject in allowed_subjects:
        return subject
    
    # Map specific frameworks/technologies to broad subjects
    subject_mapping = {
        # Python ecosystem
        "flask": "python", "django": "python", "fastapi": "python", "py": "python",
        "pandas": "python", "numpy": "python", "matplotlib": "python", "scikit": "python",
        "tensorflow": "python", "pytorch": "python", "jupyter": "python",
        "langchain": "python", "streamlit": "python", "openai": "python",
        
        # React ecosystem
        "nextjs": "react", "next.js": "react", "jsx": "react", "tsx": "react",
        "hooks": "react", "redux": "react", "component": "react",
        
        # Vue ecosystem
        "vuejs": "vue", "vue.js": "vue", "nuxt": "vue", "vuex": "vue",
        
        # Java ecosystem
        "spring": "java", "springboot": "java", "spring boot": "java", 
        "hibernate": "java", "maven": "java", "gradle": "java", "jpa": "java",
        
        # JavaScript ecosystem
        "nodejs": "javascript", "node.js": "javascript", "node": "javascript",
        "express": "javascript", "expressjs": "javascript", "js": "javascript",
        "npm": "javascript", "yarn": "javascript", "webpack": "javascript", "babel": "javascript",
        
        # Database
        "sql": "database", "mysql": "database", "postgresql": "database", 
        "mongodb": "database", "db": "database",
        
        # Web development
        "html": "web", "css": "web", "bootstrap": "web", "tailwind": "web",
        "sass": "web", "scss": "web",
        
        # Mobile development
        "android": "mobile", "kotlin": "mobile", "swift": "mobile", "ios": "mobile",
        "flutter": "mobile", "dart": "mobile", "react native": "mobile",
        
        # DevOps/Cloud
        "docker": "devops", "kubernetes": "devops", "aws": "devops", "azure": "devops",
        "gcp": "devops", "ci/cd": "devops", "jenkins": "devops"
    }
    
    # Return mapped subject or default to python
    return subject_mapping.get(subject, "python")

def normalize_subject(subject: str) -> str:
    """Main subject normalization function - tries AI first, falls back to manual"""
    return normalize_subject_with_ai(subject)

def extract_subject_and_timing(message: str) -> tuple:
    """Extract subject and timing from user message.
    
    IMPORTANT: Always returns BROAD SUBJECT CATEGORIES only:
    - python, react, vue, java, javascript, database, web, mobile, devops
    - Never returns specific frameworks like 'flask', 'fastapi', 'nextjs', etc.
    """
    message_lower = message.lower()
    
    # Find the most relevant subject from the message
    subject = "python"  # default
    
    # Check for subject keywords in order of specificity
    subject_keywords = {
        "react": ["react", "jsx", "tsx", "next.js", "nextjs", "hooks", "redux", "component"],
        "vue": ["vue", "vuejs", "vue.js", "nuxt", "vuex"],
        "java": ["java", "spring", "springboot", "hibernate", "maven", "gradle", "jpa"],
        "javascript": ["javascript", "js", "node", "nodejs", "express", "npm", "yarn", "webpack", "babel"],
        "python": ["python", "py", "flask", "django", "fastapi", "pandas", "numpy", "matplotlib", "scikit", "tensorflow", "pytorch", "jupyter"],
        "database": ["sql", "mysql", "postgresql", "mongodb", "database", "db"],
        "web": ["html", "css", "bootstrap", "tailwind", "sass", "scss"],
        "mobile": ["android", "kotlin", "swift", "ios", "flutter", "dart", "react native"],
        "devops": ["docker", "kubernetes", "aws", "azure", "gcp", "devops", "ci/cd", "jenkins"]
    }
    
    # Find the first matching subject
    for broad_subject, keywords in subject_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            subject = broad_subject
            break
    
    # Double-check with normalize_subject to ensure consistency
    subject = normalize_subject(subject)
    
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

def get_teacher_sessions_with_filter(teacher_id: str, filter_type: str = "all") -> list:
    """Get all sessions for a teacher with optional date filtering"""
    try:
        print(f"🔄 Getting sessions for teacher {teacher_id} with filter: {filter_type}")
        
        # Get all sessions for the teacher
        query = supabase.table('sessions').select('*').eq('teacher_id', teacher_id)
        
        # Apply status filter - get all sessions, not just active ones
        sessions_response = query.execute()
        sessions = sessions_response.data
        
        if not sessions:
            print(f"📭 No sessions found for teacher {teacher_id}")
            return []
        
        # Get enrollment counts for all sessions
        enrollments_response = supabase.table('session_enrollments').select('session_id').execute()
        enrollment_counts = {}
        
        for enrollment in enrollments_response.data:
            session_id = enrollment['session_id']
            enrollment_counts[session_id] = enrollment_counts.get(session_id, 0) + 1
        
        # Apply date filtering and add enrollment counts
        today = datetime.now().date()
        filtered_sessions = []
        
        for session in sessions:
            session_date = datetime.strptime(session['date'], '%Y-%m-%d').date()
            
            # Add actual enrollment count
            session['total_students'] = enrollment_counts.get(session['id'], 0)
            
            if filter_type == "all":
                filtered_sessions.append(session)
            elif filter_type == "today_future":
                if session_date >= today:
                    filtered_sessions.append(session)
            elif filter_type == "today":
                if session_date == today:
                    filtered_sessions.append(session)
            elif filter_type == "future":
                if session_date > today:
                    filtered_sessions.append(session)
        
        # Sort by date and time
        filtered_sessions.sort(key=lambda x: (x['date'], x['start_time']))
        
        print(f"✅ Found {len(filtered_sessions)} sessions for teacher {teacher_id} (filter: {filter_type})")
        return filtered_sessions
        
    except Exception as e:
        print(f"❌ Error getting teacher sessions: {e}")
        return []

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
        
        # Check for subject keywords - comprehensive list
        subject_keywords = [
            # Python ecosystem
            "python", "py", "flask", "django", "fastapi", "pandas", "numpy", "matplotlib", "scikit", "tensorflow", "pytorch", "jupyter",
            # JavaScript ecosystem  
            "javascript", "js", "node", "nodejs", "express", "expressjs", "npm", "yarn", "webpack", "babel",
            # React ecosystem
            "react", "jsx", "tsx", "nextjs", "next.js", "hooks", "redux", "component",
            # Vue ecosystem
            "vue", "vuejs", "vue.js", "nuxt", "vuex",
            # Java ecosystem
            "java", "spring", "springboot", "spring boot", "hibernate", "maven", "gradle", "jpa", "jsp", "servlet",
            # Database
            "sql", "mysql", "postgresql", "mongodb", "database", "db",
            # Web development
            "html", "css", "bootstrap", "tailwind", "sass", "scss",
            # Mobile
            "android", "kotlin", "swift", "ios", "flutter", "dart", "react native",
            # DevOps
            "docker", "kubernetes", "aws", "azure", "gcp", "devops", "ci/cd", "jenkins"
        ]
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
        
        # Parse date from student message - SAME LOGIC AS TEACHER
        message_lower = message.lower()
        today = datetime.now()
        
        # Flexible date parsing with typo support (same as teacher parsing)
        day_patterns = {
            0: ["monday", "mon"],  # Monday
            1: ["tuesday", "tue", "tuseday", "tues"],  # Tuesday (with typo support)
            2: ["wednesday", "wed", "wednes"],  # Wednesday
            3: ["thursday", "thu", "thurs"],  # Thursday
            4: ["friday", "fri"],  # Friday
            5: ["saturday", "sat"],  # Saturday
            6: ["sunday", "sun"]  # Sunday
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
            print(f"🗓️ Student parsed day: {list(day_patterns[target_day])[0].title()} -> {session_date}")
        elif "tomorrow" in message_lower:
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Student parsed: Tomorrow -> {session_date}")
        elif "today" in message_lower:
            session_date = today.strftime('%Y-%m-%d')
            print(f"🗓️ Student parsed: Today -> {session_date}")
        else:
            # Default to tomorrow if no specific date mentioned
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Student default: Tomorrow -> {session_date}")
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "preferred_start_time": start_time,
            "preferred_end_time": end_time,
            "session_date": session_date,
            "parsed_message": f"Student {student_id} wants {subject} session on {session_date} from {start_time[:5]} to {end_time[:5]}"
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
        
        # VALIDATION: Ensure only broad subjects are used
        original_subject = subject
        subject = normalize_subject(subject)
        if original_subject != subject:
            print(f"🔄 Mapped '{original_subject}' to broad category: '{subject}'")
        
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
        
        # VALIDATION: Ensure only broad subjects are used
        original_subject = subject
        subject = normalize_subject(subject)
        if original_subject != subject:
            print(f"🔄 Mapped '{original_subject}' to broad category: '{subject}'")
        
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
            "teacher_id": "e4bcab2f-8da5-4a78-85e8-094f4d7ac308",
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
def check_teacher_availability(input: str) -> str:
    """Check if teacher is available for the proposed session time. Input: JSON with date, start_time, end_time."""
    try:
        data = json.loads(input)
        date = data["date"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        
        print(f"🔍 Checking teacher availability for {date} {start_time}-{end_time}")
        
        # Check teacher availability in database
        teacher_availability = supabase.table("teacher_availability").select("*").eq("date", date).execute()
        
        if not teacher_availability.data:
            return json.dumps({
                "available": False,
                "message": f"No teacher availability set for {date}. Teacher needs to set their availability first."
            })
        
        # Check if proposed time overlaps with teacher availability
        for availability in teacher_availability.data:
            teacher_start = availability["start_time"]
            teacher_end = availability["end_time"]
            
            # Convert to minutes for comparison
            def time_to_minutes(time_str):
                hours, minutes = map(int, time_str.split(':')[:2])
                return hours * 60 + minutes
            
            session_start_mins = time_to_minutes(start_time)
            session_end_mins = time_to_minutes(end_time)
            teacher_start_mins = time_to_minutes(teacher_start)
            teacher_end_mins = time_to_minutes(teacher_end)
            
            # Check if session time is within teacher availability
            if session_start_mins >= teacher_start_mins and session_end_mins <= teacher_end_mins:
                return json.dumps({
                    "available": True,
                    "message": f"Teacher is available from {teacher_start[:5]} to {teacher_end[:5]}"
                })
        
        # If we get here, no suitable teacher availability found
        teacher_times = [f"{avail['start_time'][:5]}-{avail['end_time'][:5]}" for avail in teacher_availability.data]
        return json.dumps({
            "available": False,
            "message": f"Teacher is not available at {start_time[:5]}-{end_time[:5]}. Teacher is available: {', '.join(teacher_times)}"
        })
        
    except Exception as e:
        return json.dumps({
            "available": False,
            "message": f"Error checking teacher availability: {e}"
        })

@tool
def analyze_timing_conflict(input: str) -> str:
    """Analyze timing conflicts and suggest optimal session timing using AI reasoning. Input: JSON with all student timings."""
    try:
        data = json.loads(input)
        student_timings = data["student_timings"]
        
        print(f"🤖 AI analyzing timing conflicts for {len(student_timings)} students")
        
        # Format the timing data for AI analysis
        timing_summary = []
        for i, (start, end) in enumerate(student_timings, 1):
            timing_summary.append(f"Student {i}: {start[:5]} - {end[:5]}")
        
        timing_text = "\n".join(timing_summary)
        
        # AI prompt for timing optimization
        ai_prompt = f"""
You are an intelligent session scheduler. Analyze these student availability timings:

{timing_text}

CRITICAL RULES:
1. If the new student's timing is more than 2 hours away from existing students, REJECT them
2. Only enroll students if there's reasonable overlap (at least 30 minutes)
3. If timings are incompatible, suggest they join existing session time or create separate session

Respond in this format:
DECISION: [ACCEPT/REJECT]
REASONING: [Your 2-3 sentence explanation]
RECOMMENDED_TIME: [HH:MM - HH:MM] (only if ACCEPT)
ACCOMMODATED: [number] students

Examples:
- If compatible: "DECISION: ACCEPT\nREASONING: Students have good overlap from 13:00-14:00.\nRECOMMENDED_TIME: 13:00 - 14:00\nACCOMMODATED: 3 students"
- If incompatible: "DECISION: REJECT\nREASONING: New student wants 16:00-17:00 but existing session is 12:00-14:00, too far apart.\nACCOMMODATED: 0 students"
"""
        
        if llm is not None:
            try:
                response = llm.invoke(ai_prompt)
                ai_decision = response.content if hasattr(response, 'content') else str(response)
                print(f"🤖 AI Decision: {ai_decision}")
                return ai_decision
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
                # Fallback to algorithmic approach
                return "AI analysis unavailable. Using algorithmic approach for timing optimization."
        else:
            return "AI analysis unavailable. Using algorithmic approach for timing optimization."
            
    except Exception as e:
        return f"Error in timing analysis: {e}"

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
        
        # 3. Get all student timings for this session to analyze with AI
        all_availability = supabase.table("student_availability").select("start_time, end_time").eq("session_id", session_id).execute()
        
        student_timings = [(avail["start_time"], avail["end_time"]) for avail in all_availability.data]
        
        # 4. Use AI to analyze timing conflicts and decide whether to enroll student
        if llm is not None:
            try:
                ai_analysis_input = json.dumps({"student_timings": student_timings})
                ai_decision = analyze_timing_conflict(ai_analysis_input)
                print(f"🤖 AI Timing Decision: {ai_decision}")
                
                # Check if AI decided to REJECT the student
                if "DECISION: REJECT" in ai_decision:
                    print("❌ AI rejected student enrollment due to incompatible timing")
                    return f"❌ Your timing ({preferred_start[:5]}-{preferred_end[:5]}) is not compatible with the existing session. The current session is scheduled for a different time. Would you like to join the existing session time instead, or shall I create a separate session for you?"
                
                # Extract timing from AI response (look for HH:MM - HH:MM pattern)
                import re
                time_match = re.search(r'RECOMMENDED_TIME:\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})', ai_decision)
                if time_match:
                    start_hour, start_min, end_hour, end_min = time_match.groups()
                    optimal_start = f"{int(start_hour):02d}:{start_min}:00"
                    optimal_end = f"{int(end_hour):02d}:{end_min}:00"
                    print(f"✅ AI approved enrollment with timing: {optimal_start} - {optimal_end}")
                    
                    # Check teacher availability for the proposed time
                    teacher_check_input = json.dumps({
                        "date": date,
                        "start_time": optimal_start,
                        "end_time": optimal_end
                    })
                    teacher_availability = check_teacher_availability(teacher_check_input)
                    teacher_data = json.loads(teacher_availability)
                    
                    if not teacher_data["available"]:
                        print("❌ Teacher not available for proposed time")
                        return f"❌ {teacher_data['message']} Please choose a time when the teacher is available."
                    
                else:
                    # Fallback to algorithmic approach
                    optimal_start, optimal_end = calculate_optimal_timing(student_timings)
                    print("⚠️ AI timing extraction failed, using algorithmic approach")
            except Exception as e:
                print(f"⚠️ AI timing analysis failed: {e}")
                optimal_start, optimal_end = calculate_optimal_timing(student_timings)
        else:
            # Fallback to algorithmic approach when AI is not available
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
        if "monday" in message_lower:
            # Find next Monday
            days_ahead = 0 - today.weekday()  # Monday is 0
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "tuesday" in message_lower:
            # Find next Tuesday
            days_ahead = 1 - today.weekday()  # Tuesday is 1
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "wednesday" in message_lower:
            # Find next Wednesday
            days_ahead = 2 - today.weekday()  # Wednesday is 2
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "thursday" in message_lower:
            # Find next Thursday
            days_ahead = 3 - today.weekday()  # Thursday is 3
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "friday" in message_lower:
            # Find next Friday
            days_ahead = 4 - today.weekday()  # Friday is 4
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "saturday" in message_lower:
            # Find next Saturday
            days_ahead = 5 - today.weekday()  # Saturday is 5
            if days_ahead <= 0:
                days_ahead += 7
            target_date = today + timedelta(days=days_ahead)
            date = target_date.strftime('%Y-%m-%d')
        elif "sunday" in message_lower:
            # Find next Sunday
            days_ahead = 6 - today.weekday()  # Sunday is 6
            if days_ahead <= 0:
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
        
        # Simple teacher verification - if this is the designated teacher ID, allow it
        TEACHER_ID = 'e4bcab2f-8da5-4a78-85e8-094f4d7ac308'
        if teacher_id != TEACHER_ID:
            print(f"❌ Teacher ID {teacher_id} is not authorized")
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
    set_teacher_availability,
    analyze_timing_conflict,
    check_teacher_availability
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
        print("✅ LangGraph agent created successfully")
    except Exception as e:
        print(f"❌ Error creating LangGraph agent: {e}")
        graph = None
else:
    graph = None
    print("⚠️ LangGraph agent not created - using mock responses")

# Test function
if __name__ == "__main__":
    print("🧪 Testing simplified AI session agent...")
    result = run_session_agent("Student test123: I want a Python session 2-3 PM")
    print(f"Result: {result}")