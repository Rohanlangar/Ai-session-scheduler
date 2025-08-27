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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback if python-dotenv is not available
    pass

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
    """Extract time information from user message"""
    message_lower = message.lower()
    
    # Enhanced time patterns with better range support
    time_patterns = [
        # Pattern 1: "9am to 5pm", "10am-3pm", "2-4pm"
        r'(\d{1,2})\s*(am|pm)\s*(?:to|-)\s*(\d{1,2})\s*(am|pm)',
        # Pattern 2: "9-5pm" (both times same am/pm)
        r'(\d{1,2})\s*-\s*(\d{1,2})\s*(am|pm)',
        # Pattern 3: "2:30-4:30pm"
        r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)',
        # Pattern 4: Single time "2pm"
        r'(\d{1,2})\s*(am|pm)',
    ]
    
    for i, pattern in enumerate(time_patterns):
        match = re.search(pattern, message_lower)
        if match:
            groups = match.groups()
            print(f"🕐 Pattern {i+1} matched: {groups}")
            
            if i == 0:  # "9am to 5pm" or "10am-3pm"
                start_hour = int(groups[0])
                start_ampm = groups[1]
                end_hour = int(groups[2])
                end_ampm = groups[3]
                
                # Convert start time
                if start_ampm == 'pm' and start_hour < 12:
                    start_hour += 12
                elif start_ampm == 'am' and start_hour == 12:
                    start_hour = 0
                
                # Convert end time
                if end_ampm == 'pm' and end_hour < 12:
                    end_hour += 12
                elif end_ampm == 'am' and end_hour == 12:
                    end_hour = 0
                
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
                
            elif i == 1:  # "9-5pm" (both same am/pm)
                start_hour = int(groups[0])
                end_hour = int(groups[1])
                am_pm = groups[2]
                
                # Convert both times
                if am_pm == 'pm':
                    if start_hour < 12:
                        start_hour += 12
                    if end_hour < 12:
                        end_hour += 12
                elif am_pm == 'am':
                    if start_hour == 12:
                        start_hour = 0
                    if end_hour == 12:
                        end_hour = 0
                
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
                
            elif i == 2:  # "2:30-4:30pm"
                start_hour = int(groups[0])
                start_min = int(groups[1])
                end_hour = int(groups[2])
                end_min = int(groups[3])
                am_pm = groups[4]
                
                # Convert times
                if am_pm == 'pm':
                    if start_hour < 12:
                        start_hour += 12
                    if end_hour < 12:
                        end_hour += 12
                elif am_pm == 'am':
                    if start_hour == 12:
                        start_hour = 0
                    if end_hour == 12:
                        end_hour = 0
                
                return f"{start_hour:02d}:{start_min:02d}:00", f"{end_hour:02d}:{end_min:02d}:00"
                
            elif i == 3:  # Single time "2pm"
                start_hour = int(groups[0])
                am_pm = groups[1]
                
                if am_pm == 'pm' and start_hour < 12:
                    start_hour += 12
                elif am_pm == 'am' and start_hour == 12:
                    start_hour = 0
                
                end_hour = start_hour + 1
                return f"{start_hour:02d}:00:00", f"{end_hour:02d}:00:00"
    
    print("🕐 No time pattern matched, using default")
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
        
        # Strategy: Find exact majority preference (most common time slot)
        # Count frequency of each unique time slot
        time_counts = {}
        for start_mins, end_mins in time_ranges:
            time_key = (start_mins, end_mins)
            time_counts[time_key] = time_counts.get(time_key, 0) + 1
        
        # Find the most popular time slot
        most_popular_time = max(time_counts.items(), key=lambda x: x[1])
        popular_start_mins, popular_end_mins = most_popular_time[0]
        student_count = most_popular_time[1]
        
        print(f"  Most popular time slot: {popular_start_mins//60:02d}:{popular_start_mins%60:02d} - {popular_end_mins//60:02d}:{popular_end_mins%60:02d}")
        print(f"  Preferred by {student_count} out of {len(time_ranges)} students")
        
        # Use the most popular time slot directly
        optimal_start = f"{popular_start_mins//60:02d}:{popular_start_mins%60:02d}:00"
        optimal_end = f"{popular_end_mins//60:02d}:{popular_end_mins%60:02d}:00"
        
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
You are an intelligent AI session scheduler. Your role is determined by the user type:

**FOR TEACHERS (user_id = e4bcab2f-8da5-4a78-85e8-094f4d7ac308):**
- ONLY job: Set teacher availability using parse_teacher_availability() and set_teacher_availability()
- Teachers can teach ANY subject - don't ask for subject clarification
- Return the exact result from set_teacher_availability() tool

**FOR ALL OTHER USERS (Students):**
- IMMEDIATELY use tools, do NOT explain what you're doing
- Follow this workflow EXACTLY:
  1. Call parse_student_request() with student_id and message
  2. Call create_new_session() with the parsed data (this handles everything automatically)
  3. Return the EXACT result from create_new_session() tool

**RESPONSE FORMAT:**
- Use tools immediately, no explanations
- Return the EXACT tool result as your final response
- Do NOT add any additional text or explanations
- Example: If tool returns "Python session created at 12:00-13:00", return exactly that

**CRITICAL RULES:**
- ALWAYS return the exact tool result as your final response
- Do NOT modify or add to the tool result
- Do NOT explain what you're doing
- Just call the tool and return its result
"""

def validate_input(message: str) -> tuple:
    """Validate user input and return (is_valid, error_message)"""
    if not message or len(message.strip()) < 3:
        return False, "Please tell me what you want to learn."
    
    # Check for basic session keywords
    session_keywords = ['session', 'class', 'lesson', 'learn', 'teach', 'available', 'want', 'need']
    if not any(keyword in message.lower() for keyword in session_keywords):
        return False, "What subject do you want to learn?"
    
    return True, ""

def safe_ai_invoke(messages: list, fallback_message: str = "I'll help you with your session request.") -> str:
    """Safely invoke AI agent with tools for actual session creation"""
    try:
        if llm is None or graph is None:
            print("⚠️ LLM or graph is None, using fallback")
            return fallback_message
        
        print(f"🤖 Using LangGraph agent with tools")
        
        # Convert messages to LangChain format
        from langchain_core.messages import SystemMessage, HumanMessage
        
        langchain_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                langchain_messages.append(SystemMessage(content=msg.get("content", "")))
            elif msg.get("role") == "user":
                langchain_messages.append(HumanMessage(content=msg.get("content", "")))
        
        # Invoke the agent with tools
        try:
            result = graph.invoke({"messages": langchain_messages})
            
            # Extract the final response - handle different result formats
            if result:
                print(f"🔍 Agent result type: {type(result)}")
                print(f"🔍 Agent result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
                
                if isinstance(result, dict) and "messages" in result:
                    final_message = result["messages"][-1]
                    if hasattr(final_message, 'content'):
                        response_content = final_message.content
                        print(f"✅ Agent response: {response_content[:100]}...")
                        return response_content
                    else:
                        print(f"⚠️ Final message has no content: {final_message}")
                        return fallback_message
                elif isinstance(result, list) and len(result) > 0:
                    # Sometimes the result is directly a list of messages
                    final_message = result[-1]
                    if hasattr(final_message, 'content'):
                        response_content = final_message.content
                        print(f"✅ Agent response (list): {response_content[:100]}...")
                        return response_content
                    else:
                        print(f"⚠️ Final message in list has no content: {final_message}")
                        return fallback_message
                else:
                    print(f"⚠️ Unexpected result format: {result}")
                    return fallback_message
            else:
                print(f"⚠️ Agent result is None or empty")
                return fallback_message
                
        except Exception as agent_error:
            print(f"❌ Agent invocation failed: {agent_error}")
            # Fallback to direct LLM call without tools
            print(f"🔄 Falling back to direct LLM call")
            
            system_msg = ""
            user_msg = ""
            
            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content", "")
                elif msg.get("role") == "user":
                    user_msg = msg.get("content", "")
            
            full_prompt = f"{system_msg}\n\nUser Request: {user_msg}"
            response = llm.invoke(full_prompt)
            
            if hasattr(response, 'content') and response.content:
                print(f"✅ Fallback LLM response: {response.content[:100]}...")
                return response.content
            else:
                return fallback_message
        
    except Exception as e:
        print(f"❌ Safe AI invoke failed: {e}")
        import traceback
        traceback.print_exc()
        return fallback_message

def run_session_agent(user_input: str) -> str:
    """Run the session creation agent with user input - DIRECT APPROACH to avoid rate limits."""
    try:
        # Extract user information from the message
        user_id, is_teacher_from_message, clean_message = extract_user_id_from_message(user_input)
        
        print(f"🔍 Processing - User ID: {user_id}, Message: {clean_message}")
        
        # SIMPLIFIED ROLE DETECTION - Only check user ID
        is_designated_teacher = (user_id == TEACHER_ID)
        
        if is_designated_teacher:
            # TEACHER WORKFLOW - Direct tool calls
            print(f"👨‍🏫 TEACHER detected: {user_id}")
            try:
                # Parse teacher availability
                teacher_input = json.dumps({
                    "teacher_id": user_id,
                    "message": clean_message
                })
                parsed_result = parse_teacher_availability.invoke(teacher_input)
                parsed_data = json.loads(parsed_result)
                
                if 'error' in parsed_data:
                    return parsed_data['error']
                
                # Set teacher availability
                availability_input = json.dumps({
                    "teacher_id": user_id,
                    "date": parsed_data["date"],
                    "start_time": parsed_data["start_time"],
                    "end_time": parsed_data["end_time"]
                })
                result = set_teacher_availability.invoke(availability_input)
                return result
                
            except Exception as e:
                print(f"❌ Teacher workflow error: {e}")
                return "✅ I'll help you set your availability. Please specify the day and time."
        
        else:
            # STUDENT WORKFLOW - Direct tool calls
            print(f"👨‍🎓 STUDENT detected: {user_id}")
            
            # Validate input for students only
            is_valid, error_msg = validate_input(clean_message)
            if not is_valid:
                return error_msg
            
            try:
                # Parse student request
                student_input = json.dumps({
                    "student_id": user_id,
                    "message": clean_message
                })
                parsed_result = parse_student_request.invoke(student_input)
                parsed_data = json.loads(parsed_result)
                
                if 'error' in parsed_data:
                    return parsed_data['error']
                
                # Create/update session directly
                session_input = json.dumps({
                    "student_id": parsed_data["student_id"],
                    "subject": parsed_data["subject"],
                    "date": parsed_data["session_date"],
                    "start_time": parsed_data["preferred_start_time"],
                    "end_time": parsed_data["preferred_end_time"]
                })
                result = create_new_session.invoke(session_input)
                return result
                
            except Exception as e:
                print(f"❌ Student workflow error: {e}")
                return "✅ I'll help you book a session. Please specify the subject, day, and time."
        
    except Exception as e:
        print(f"❌ ERROR in run_session_agent: {e}")
        return "I'm having trouble processing your request. Please try again with a clear session request (e.g., 'I want Python session 2-3pm Monday')."

# === HELPER FUNCTIONS ===

def normalize_subject_with_ai(subject: str) -> str:
    """Use AI to intelligently map any subject to broad categories.
    
    This allows for flexible subject recognition including new technologies
    like LangChain, Streamlit, AI, Machine Learning, etc.
    """
    try:
        # Initialize Claude
        claude = ChatAnthropic(
            model="claude-3-haiku-20240307",
            api_key=ANTHROPIC_API_KEY,
            temperature=0
        )
        
        prompt = f"""
        Map the following technology/subject to ONE of these broad categories:
        - python (for Python, Django, Flask, FastAPI, Streamlit, pandas, AI, Machine Learning, OpenAI, etc.)
        - react (for React, Next.js, JSX, Redux, Gatsby, etc.)
        - vue (for Vue.js, Nuxt, Vuex, etc.)  
        - java (for Java, Spring, Hibernate, Spring Boot, etc.)
        - javascript (for Node.js, Express, vanilla JS, TypeScript, etc.)
        - database (for SQL, MySQL, MongoDB, PostgreSQL, etc.)
        - web (for HTML, CSS, Bootstrap, Tailwind, SASS, etc.)
        - mobile (for Android, iOS, Flutter, React Native, Swift, Kotlin, etc.)
        - devops (for Docker, Kubernetes, AWS, Azure, GCP, CI/CD, Jenkins, etc.)
        
        Subject to map: "{subject}"
        
        Return ONLY the broad category name (e.g., "python", "react", etc.). No explanation needed.
        """
        
        response = claude.invoke(prompt)
        mapped_subject = response.content.strip().lower()
        
        # Validate the response is one of our allowed subjects
        allowed_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops"]
        if mapped_subject in allowed_subjects:
            print(f"🤖 AI mapped '{subject}' → '{mapped_subject}'")
            return mapped_subject
        else:
            print(f"⚠️ AI returned invalid subject '{mapped_subject}', defaulting to 'python'")
            return "python"
            
    except Exception as e:
        print(f"❌ AI subject mapping failed: {e}")
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
    """Use AI to extract subject and timing from user message with retry logic and caching."""
    import time
    import hashlib
    
    # Simple in-memory cache to reduce API calls
    if not hasattr(extract_subject_and_timing_with_ai, 'cache'):
        extract_subject_and_timing_with_ai.cache = {}
    
    # Create cache key
    cache_key = hashlib.md5(message.lower().encode()).hexdigest()
    if cache_key in extract_subject_and_timing_with_ai.cache:
        cached_result = extract_subject_and_timing_with_ai.cache[cache_key]
        print(f"🔄 Using cached result for similar message")
        return cached_result
    
    max_retries = 1  # Single retry to fail very fast
    base_delay = 0.2  # Very short delay
    
    for attempt in range(max_retries):
        try:
            claude = ChatAnthropic(
                model="claude-3-haiku-20240307", 
                api_key=ANTHROPIC_API_KEY,
                temperature=0
            )
            
            prompt = f"""
            You are an intelligent session scheduler. Extract the subject and timing from this student message:
            "{message}"
            
            SUBJECT MAPPING - Be flexible and intelligent:
            - python: Python, Django, Flask, FastAPI, Streamlit, pandas, numpy, AI, ML, machine learning, data science, LangChain, OpenAI, ChatGPT, artificial intelligence, deep learning, neural networks, TensorFlow, PyTorch, scikit-learn
            - react: React, ReactJS, Next.js, JSX, Redux, Gatsby, React Native (web focus)
            - vue: Vue, Vue.js, Vuejs, Nuxt, Vuex, Vue 3
            - java: Java, Spring, Spring Boot, Hibernate, Maven, Gradle, JPA, JSP, Servlets
            - javascript: JavaScript, JS, Node.js, Express, TypeScript, TS, vanilla JS, ES6, npm, yarn
            - database: SQL, MySQL, PostgreSQL, MongoDB, database, DB, SQLite, Redis, NoSQL, queries, data modeling
            - web: HTML, CSS, Bootstrap, Tailwind, SASS, SCSS, web development, frontend, responsive design, CSS Grid, Flexbox
            - mobile: Android, iOS, Flutter, React Native (mobile focus), Swift, Kotlin, mobile development, app development
            - devops: Docker, Kubernetes, AWS, Azure, GCP, Jenkins, CI/CD, DevOps, deployment, cloud, infrastructure, containers
            
            INTELLIGENT SUBJECT DETECTION:
            - If message mentions specific technologies, map to appropriate category
            - If message is vague like "coding", "programming", "development" without specifics, return "UNCLEAR"
            - If message mentions multiple subjects, pick the most prominent one
            - Be flexible with variations and typos (e.g., "Reactjs" → react, "Pyhton" → python)
            
            TIMING EXTRACTION:
            - Look for patterns like "2-3pm", "14:00-15:00", "2 to 3", "from 2 to 3"
            - Default to 14:00-15:00 if no clear time mentioned
            - Convert 12-hour to 24-hour format
            
            Respond in this EXACT format:
            SUBJECT: [category or UNCLEAR]
            START_TIME: [HH:MM:SS]  
            END_TIME: [HH:MM:SS]
            
            Examples:
            "I want React session 2-3pm" → SUBJECT: react, START_TIME: 14:00:00, END_TIME: 15:00:00
            "Need help with coding" → SUBJECT: UNCLEAR, START_TIME: 14:00:00, END_TIME: 15:00:00
            "Docker training tomorrow" → SUBJECT: devops, START_TIME: 14:00:00, END_TIME: 15:00:00
            """
            
            response = claude.invoke(prompt)
            ai_response = response.content if hasattr(response, 'content') else str(response)
            
            # Parse AI response
            subject = None  # ✅ Changed: No default, let manual extraction handle it
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
            
            # Handle AI response
            valid_subjects = ["python", "react", "vue", "java", "javascript", "database", "web", "mobile", "devops", "genai", "ai", "ml"]
            
            result = None
            if subject == "unclear":
                print(f"🤖 AI determined subject is UNCLEAR from message: '{message}'")
                result = (None, start_time, end_time)  # Return None to trigger error message
            elif subject and subject in valid_subjects:
                print(f"🤖 AI extracted - Subject: {subject}, Time: {start_time}-{end_time}")
                result = (subject, start_time, end_time)
            else:
                print(f"⚠️ AI returned unexpected subject: {subject}, trying manual extraction")
                result = extract_subject_and_timing_manual(message)
            
            # Cache successful AI results
            if result and result[0] is not None:
                extract_subject_and_timing_with_ai.cache[cache_key] = result
            
            return result
                
        except Exception as e:
            error_msg = str(e)
            
            # Check for rate limiting (529 error) - fail fast
            if "529" in error_msg or "overloaded" in error_msg.lower():
                print(f"❌ AI rate limited, immediately using manual extraction")
                break  # Skip retries for rate limiting
            else:
                print(f"❌ AI extraction failed: {e}, using manual method")
                break  # Skip retries for other errors too
            
            # Fallback to manual extraction
            return extract_subject_and_timing_manual(message)
    
    # If all retries failed, use manual extraction
    return extract_subject_and_timing_manual(message)

def extract_subject_and_timing_manual(message: str) -> tuple:
    """Enhanced manual fallback with fuzzy matching and intelligent detection"""
    import difflib
    message_lower = message.lower().strip()
    
    # Enhanced subject mappings with comprehensive coverage
    subject_mappings = {
        "python": {
            "exact": ["python", "py"],
            "frameworks": ["django", "flask", "fastapi", "streamlit", "tornado"],
            "libraries": ["pandas", "numpy", "matplotlib", "scipy", "requests"],
            "ai_ml": ["tensorflow", "pytorch", "scikit-learn", "keras", "langchain", "openai", "chatgpt", "ai", "ml", "machine learning", "deep learning", "neural networks", "data science", "nlp"],
            "typos": ["pyhton", "pythn", "phyton"]  # Common typos
        },
        "react": {
            "exact": ["react", "reactjs", "react.js"],
            "frameworks": ["nextjs", "next.js", "gatsby", "remix"],
            "libraries": ["redux", "mobx", "recoil", "zustand"],
            "concepts": ["jsx", "hooks", "components"]
        },
        "vue": {
            "exact": ["vue", "vuejs", "vue.js"],
            "frameworks": ["nuxt", "nuxtjs", "quasar"],
            "libraries": ["vuex", "pinia", "vue-router"],
            "concepts": ["composition api", "options api"]
        },
        "java": {
            "exact": ["java"],
            "frameworks": ["spring", "spring boot", "hibernate", "struts"],
            "tools": ["maven", "gradle"],
            "concepts": ["jvm", "jpa", "jsp", "servlets"]
        },
        "javascript": {
            "exact": ["javascript", "js"],
            "runtime": ["nodejs", "node.js", "deno"],
            "frameworks": ["express", "koa", "nestjs"],
            "concepts": ["typescript", "es6", "npm", "yarn"]
        },
        "database": {
            "sql": ["mysql", "postgresql", "sqlite", "oracle"],
            "nosql": ["mongodb", "redis", "cassandra"],
            "concepts": ["sql", "database", "db", "queries", "data modeling"]
        },
        "web": {
            "markup": ["html", "html5"],
            "styling": ["css", "css3", "sass", "scss"],
            "frameworks": ["bootstrap", "tailwind", "bulma"],
            "concepts": ["responsive design", "flexbox", "grid", "frontend"]
        },
        "mobile": {
            "native": ["android", "ios", "swift", "kotlin"],
            "cross_platform": ["flutter", "react native", "xamarin"],
            "concepts": ["mobile development", "app development", "mobile app"]
        },
        "devops": {
            "containers": ["docker", "kubernetes", "podman"],
            "cloud": ["aws", "azure", "gcp", "google cloud"],
            "ci_cd": ["jenkins", "github actions", "gitlab ci"],
            "concepts": ["devops", "deployment", "infrastructure", "cloud", "containers"]
        }
    }
    
    # Create flat keyword mapping for exact matches
    keyword_to_subject = {}
    all_keywords = []
    for subject, categories in subject_mappings.items():
        for category, keywords in categories.items():
            for keyword in keywords:
                keyword_to_subject[keyword.lower()] = subject
                all_keywords.append(keyword.lower())
    
    # Ordered keywords - longer/more specific terms first to avoid conflicts
    priority_keywords = [
        # Multi-word phrases first (most specific)
        ("machine learning", "python"), ("spring boot", "java"), ("next.js", "react"),
        ("deep learning", "python"), ("data science", "python"), ("react native", "mobile"),
        ("mobile app", "mobile"), ("app development", "mobile"),
        
        # Technology-specific terms
        ("javascript", "javascript"), ("typescript", "javascript"), ("nodejs", "javascript"), ("node.js", "javascript"),
        ("python", "python"), ("django", "python"), ("flask", "python"), ("fastapi", "python"),
        ("react", "react"), ("reactjs", "react"), ("nextjs", "react"), ("jsx", "react"),
        ("vue", "vue"), ("vuejs", "vue"), ("vue.js", "vue"), ("nuxt", "vue"),
        ("java", "java"), ("spring", "java"), ("hibernate", "java"),
        
        # AI/ML terms
        ("tensorflow", "python"), ("pytorch", "python"), ("langchain", "python"), ("openai", "python"),
        ("chatgpt", "python"), ("ai", "python"), ("ml", "python"),
        
        # Web technologies
        ("html", "web"), ("css", "web"), ("bootstrap", "web"), ("tailwind", "web"),
        
        # DevOps
        ("docker", "devops"), ("kubernetes", "devops"), ("aws", "devops"), ("azure", "devops"),
        
        # Database
        ("mongodb", "database"), ("mysql", "database"), ("postgresql", "database"), ("sqlite", "database"),
        
        # Mobile
        ("android", "mobile"), ("ios", "mobile"), ("flutter", "mobile"), ("swift", "mobile"), ("kotlin", "mobile"),
        
        # Short forms (last to avoid conflicts)
        ("js", "javascript"), ("py", "python"),
    ]
    
    # Check priority keywords in order (most specific first)
    for keyword, subject in priority_keywords:
        if keyword in message_lower:
            print(f"🔍 Fast manual: found '{keyword}' → '{subject}'")
            start_time, end_time = parse_time_from_message(message)
            return subject, start_time, end_time
    
    # Simple typo handling for most common cases
    typo_fixes = [
        ("pyhton", "python"), ("pythn", "python"), ("phyton", "python"),
        ("reactjs", "react"), ("reakt", "react"), ("reat", "react"),
        ("javascrip", "javascript"), ("javas", "java"),
    ]
    
    for typo, correct in typo_fixes:
        if typo in message_lower:
            print(f"🔍 Fast manual: typo fix '{typo}' → '{correct}'")
            start_time, end_time = parse_time_from_message(message)
            return correct, start_time, end_time
    
    # Check for vague patterns that should return None
    vague_patterns = [
        "help with coding", "teach me programming", "learn development", 
        "help with my project", "coding help", "programming help",
        "can you teach me", "i need help", "help me learn"
    ]
    
    if any(pattern in message_lower for pattern in vague_patterns):
        print(f"⚠️ Enhanced manual: Detected vague request pattern")
        start_time, end_time = parse_time_from_message(message)
        return None, start_time, end_time
    
    # Context-based intelligent guessing
    context_hints = {
        "frontend": "react", "backend": "python", "fullstack": "python",
        "website": "web", "web development": "web", "ui": "react",
        "server": "python", "api": "python", "microservice": "java",
        "data analysis": "python", "analytics": "python", "visualization": "python",
        "mobile app": "mobile", "app development": "mobile", "android app": "mobile",
        "cloud deployment": "devops", "infrastructure": "devops", "containerization": "devops"
    }
    
    for hint, subject in context_hints.items():
        if hint in message_lower:
            print(f"🔍 Enhanced manual: context hint '{hint}' → '{subject}'")
            start_time, end_time = parse_time_from_message(message)
            return subject, start_time, end_time
    
    # ✅ SAFE: Return None if no clear subject found
    print(f"⚠️ Enhanced manual: No clear subject found in '{message}'")
    start_time, end_time = parse_time_from_message(message)
    return None, start_time, end_time

# === SIMPLIFIED TOOLS FOR AI AGENT ===

@tool
def get_current_date() -> str:
    """Get today's date for session scheduling."""
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"📅 Current date: {today}")
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
    """Parse student message to extract subject, timing preferences using AI. Input: JSON with student_id, message."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        message = data["message"]
        
        print(f"📝 AI parsing student request: {message}")
        
        # Validate message has basic requirements
        if not message or len(message.strip()) < 5:
            return json.dumps({
                "error": "Please provide more details about your session request (subject, time, day)."
            })
        
        # Use AI for intelligent subject and timing extraction
        subject, start_time, end_time = extract_subject_and_timing_with_ai(message)
        
        # Enhanced subject validation with intelligent suggestions
        if not subject or subject == "unknown" or subject is None:
            # Generate contextual suggestions based on message content
            suggestions = []
            message_lower = message.lower()
            
            if any(word in message_lower for word in ["web", "frontend", "ui", "website"]):
                suggestions.extend(["React", "Vue", "Web Development"])
            elif any(word in message_lower for word in ["backend", "server", "api", "data"]):
                suggestions.extend(["Python", "Java", "JavaScript"])
            elif any(word in message_lower for word in ["mobile", "app"]):
                suggestions.append("Mobile Development")
            elif any(word in message_lower for word in ["cloud", "deploy", "infrastructure"]):
                suggestions.append("DevOps")
            
            if suggestions:
                suggestion_text = ", ".join(suggestions)
                error_msg = f"I couldn't determine the specific subject from your message. Based on what you mentioned, you might be interested in: {suggestion_text}. Please specify clearly (e.g., 'I want Python session 2-3pm')."
            else:
                error_msg = "Please specify which technology you'd like to learn. Popular options include: Python, React, Java, JavaScript, Vue, Mobile Development, DevOps, or Web Development. Example: 'I want Python session 2-3pm Monday'."
            
            return json.dumps({
                "error": error_msg
            })
        
        # Validate time format
        try:
            # Check if times are valid
            start_hour = int(start_time.split(':')[0])
            end_hour = int(end_time.split(':')[0])
            if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
                return json.dumps({
                    "error": "Please provide valid times (0-23 hours format)."
                })
            if start_hour >= end_hour:
                return json.dumps({
                    "error": "Start time must be before end time."
                })
        except:
            return json.dumps({
                "error": "Please provide clear time format (e.g., '2-3pm', '14:00-15:00')."
            })
        
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
            print(f"🗓️ Student parsed day: {list(day_patterns[target_day])[0].title()} → {session_date}")
        elif "tomorrow" in message_lower:
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Student parsed: Tomorrow → {session_date}")
        elif "today" in message_lower:
            session_date = today.strftime('%Y-%m-%d')
            print(f"🗓️ Student parsed: Today → {session_date}")
        else:
            # Default to tomorrow if no specific date mentioned
            session_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Student default: Tomorrow → {session_date}")
        
        result = {
            "student_id": student_id,
            "subject": subject,
            "preferred_start_time": start_time,
            "preferred_end_time": end_time,
            "session_date": session_date,
            "parsed_message": f"Student {student_id} wants {subject} session on {session_date} from {start_time[:5]} to {end_time[:5]}"
        }
        
        print(f"✅ Parsed request: {result['parsed_message']}")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        print(f"❌ Error parsing request: {e}")
        return f"Error parsing request: {e}"

@tool
def check_existing_session(input: str) -> str:
    """🤖 AI-POWERED SESSION ANALYZER: Intelligently checks for existing sessions and analyzes pending requests. Input: JSON with subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        subject = data["subject"].lower()
        date = data["date"]
        start_time = data.get("start_time", "14:00:00")
        end_time = data.get("end_time", "15:00:00")
        
        print(f"🤖 AI ANALYZER: Checking {subject} sessions on {date}")
        
        # 1. Check for existing ACTIVE sessions
        active_sessions = supabase.table('sessions').select('*').eq('subject', subject).eq('date', date).eq('status', 'active').execute()
        
        # 2. 🧠 AI INTELLIGENCE: Analyze pending requests
        pending_requests = supabase.table("student_availability").select("*").eq("subject", subject).eq("date", date).is_("session_id", "null").execute()
        
        pending_count = len(pending_requests.data)
        active_count = len(active_sessions.data)
        
        print(f"🧠 AI ANALYSIS: {active_count} active sessions, {pending_count} pending requests")
        
        if active_sessions.data:
            session = active_sessions.data[0]
            
            # 🤖 AI provides intelligent session analysis
            ai_analysis = f"""
🤖 AI FOUND EXISTING SESSION:
- Subject: {subject.upper()}
- Date: {date}
- Time: {session['start_time'][:5]}-{session['end_time'][:5]}
- Current Students: {session['total_students']}
- Session ID: {session['id']}

AI RECOMMENDATION: Join existing session for optimal scheduling.
"""
            print(ai_analysis)
            
            result = {
                "exists": True,
                "session_id": session["id"],
                "current_timing": f"{session['start_time']}-{session['end_time']}",
                "student_count": session["total_students"],
                "ai_analysis": ai_analysis,
                "message": f"🤖 SESSION EXISTS: {subject} session found on {date}. MUST use update_existing_session() to add student and optimize timing!",
                "action_required": "CALL update_existing_session() - DO NOT call create_new_session()"
            }
            return json.dumps(result, indent=2)
        
        elif pending_count > 0:
            # 🧠 AI analyzes pending patterns
            timing_patterns = {}
            for req in pending_requests.data:
                time_key = f"{req['start_time'][:5]}-{req['end_time'][:5]}"
                timing_patterns[time_key] = timing_patterns.get(time_key, 0) + 1
            
            ai_pattern_analysis = f"""
🤖 AI PATTERN ANALYSIS:
- Pending Requests: {pending_count}
- Timing Preferences: {timing_patterns}
- Status: Collecting requests for optimal scheduling

AI STRATEGY: Waiting for more requests to create majority-optimized session.
"""
            print(ai_pattern_analysis)
            
            result = {
                "exists": False,
                "pending_requests": pending_count,
                "timing_patterns": timing_patterns,
                "ai_analysis": ai_pattern_analysis,
                "message": f"🤖 NO SESSION EXISTS: No {subject} session found for {date}. MUST use create_new_session() to create first session!",
                "action_required": "CALL create_new_session() - This will be the FIRST student"
            }
            return json.dumps(result, indent=2)
        
        if sessions.data:
            session = sessions.data[0]
            result = {
                "exists": True,
                "session_id": session["id"],
                "current_timing": f"{session['start_time']}-{session['end_time']}",
                "student_count": session["total_students"],
                "message": f"Found {subject} session on {date} at {session['start_time'][:5]}-{session['end_time'][:5]}"
            }
            print(f"Found existing session: {result['message']}")
            return json.dumps(result, indent=2)
        
        # Check for time conflicts with other sessions on the same date (ONLY different subjects)
        all_sessions = supabase.table('sessions').select('*').eq('date', date).eq('status', 'active').execute()
        
        if all_sessions.data:
            # Convert time to minutes for comparison
            def time_to_minutes(time_str):
                hours, minutes = map(int, time_str.split(':')[:2])
                return hours * 60 + minutes
            
            new_start_mins = time_to_minutes(start_time)
            new_end_mins = time_to_minutes(end_time)
            
            for existing_session in all_sessions.data:
                # SKIP same subject sessions - they should be joined, not blocked
                if existing_session['subject'].lower() == subject.lower():
                    continue
                    
                existing_start_mins = time_to_minutes(existing_session['start_time'])
                existing_end_mins = time_to_minutes(existing_session['end_time'])
                
                # Check if there's any overlap with DIFFERENT subject
                if (new_start_mins < existing_end_mins and new_end_mins > existing_start_mins):
                    conflict_result = {
                        "exists": False,
                        "time_conflict": True,
                        "conflicting_session": {
                            "subject": existing_session['subject'],
                            "timing": f"{existing_session['start_time'][:5]}-{existing_session['end_time'][:5]}"
                        },
                        "message": f"Time conflict: {existing_session['subject']} session already scheduled at {existing_session['start_time'][:5]}-{existing_session['end_time'][:5]} on {date}"
                    }
                    print(f"Time conflict detected with {existing_session['subject']} session")
                    return json.dumps(conflict_result, indent=2)
        
        # No conflicts found
        result = {
            "exists": False,
            "time_conflict": False,
            "message": f"No {subject} session found for {date} and time slot is available"
        }
        print(f"No conflicts - time slot available")
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error checking existing session: {e}"


@tool
def create_new_session(input: str) -> str:
    """🤖 SMART SESSION HANDLER: Intelligently handles entire workflow - creates session for first student OR adds to existing session with AI optimization. Input: JSON with student_id, subject, date, start_time, end_time."""
    try:
        data = json.loads(input)
        student_id = data["student_id"]
        subject = data["subject"].lower()
        date = data.get("date") or data.get("session_date")  # Handle both key names
        start_time = data.get("start_time") or data.get("preferred_start_time")
        end_time = data.get("end_time") or data.get("preferred_end_time")
        
        if not date:
            return "❌ Missing date information"
        if not start_time:
            return "❌ Missing start time information"
        if not end_time:
            return "❌ Missing end time information"
        
        print(f"🤖 SMART HANDLER: Processing {student_id} request for {subject} on {date}")
        
        # 🛡️ ENHANCED CONFLICT DETECTION: Check for different subject sessions at same time
        all_sessions_same_time = supabase.table('sessions').select('*').eq('date', date).eq('status', 'active').execute()
        
        conflicting_sessions = []
        same_subject_sessions = []
        
        for session in all_sessions_same_time.data:
            session_start = session['start_time']
            session_end = session['end_time']
            session_subject = session['subject']
            
            # Check for time overlap
            if ((start_time >= session_start and start_time < session_end) or
                (end_time > session_start and end_time <= session_end) or
                (start_time <= session_start and end_time >= session_end)):
                
                if session_subject != subject:
                    conflicting_sessions.append(session)
                else:
                    same_subject_sessions.append(session)
        
        # Simplified conflict handling
        if conflicting_sessions:
            conflict_session = conflicting_sessions[0]
            conflict_subject = conflict_session['subject']
            conflict_time = f"{conflict_session['start_time'][:5]}-{conflict_session['end_time'][:5]}"
            
            return f"⚠️ Time conflict! {conflict_subject.title()} session already at {conflict_time}. Try a different time."
        
        # 1. Check for existing sessions for this subject and date
        existing_sessions = supabase.table('sessions').select('*').eq('subject', subject).eq('date', date).eq('status', 'active').execute()
        
        if existing_sessions.data:
            # SESSION EXISTS - Add student and optimize timing
            session = existing_sessions.data[0]
            session_id = session['id']
            current_timing = f"{session['start_time'][:5]}-{session['end_time'][:5]}"
            current_students = session['total_students']
            
            print(f"✅ FOUND EXISTING SESSION: {session_id} at {current_timing} with {current_students} students")
            
            # Check if student already enrolled
            existing_enrollment = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
            
            if existing_enrollment.data:
                return f"✅ You're already enrolled in the {subject} session at {current_timing}!"
            
            # Add student's availability
            availability_data = {
                "student_id": student_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "subject": subject,
                "session_id": session_id
            }
            supabase.table("student_availability").insert(availability_data).execute()
            
            # Enroll student
            supabase.table("session_enrollments").insert({
                "session_id": session_id,
                "student_id": student_id
            }).execute()
            
            new_total = current_students + 1
            print(f"✅ ENROLLED {student_id}. Now {new_total} students total.")
            
            # 🧠 AI OPTIMIZATION: Analyze ALL students for optimal timing
            all_students = supabase.table("student_availability").select("*").eq("session_id", session_id).execute()
            
            student_timings = []
            timing_summary = []
            
            for avail in all_students.data:
                student_timings.append((avail["start_time"], avail["end_time"]))
                timing_summary.append(f"{avail['student_id']}: {avail['start_time'][:5]}-{avail['end_time'][:5]}")
            
            print(f"🧠 AI ANALYZING ALL {len(student_timings)} students:")
            for summary in timing_summary:
                print(f"   {summary}")
            
            # Use AI to find optimal timing
            if llm is not None:
                try:
                    ai_prompt = f"""
🤖 DYNAMIC SESSION OPTIMIZER

CURRENT SESSION: {current_timing} with {current_students} previous students
NEW STUDENT: {student_id} prefers {start_time[:5]}-{end_time[:5]}

ALL STUDENT PREFERENCES (including new student):
{chr(10).join(timing_summary)}

TASK: Determine optimal timing for ALL {new_total} students.

Count votes for each time slot and select majority preference.

RESPOND IN FORMAT:
VOTE_ANALYSIS: [Count for each time slot]
OPTIMAL_TIME: [HH:MM-HH:MM]
MAJORITY_COUNT: [Number preferring optimal time]
REASONING: [Why this time was selected]

Example:
VOTE_ANALYSIS: 12:00-13:00 has 3 votes, 16:00-17:00 has 4 votes
OPTIMAL_TIME: 16:00-17:00
MAJORITY_COUNT: 4
REASONING: 16:00-17:00 wins with 4 votes vs 3 votes
"""
                    
                    ai_response = llm.invoke(ai_prompt)
                    ai_decision = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
                    print(f"🤖 AI ANALYSIS:\n{ai_decision}")
                    
                    # Extract optimal timing
                    time_match = re.search(r'OPTIMAL_TIME:\s*(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', ai_decision)
                    if time_match:
                        start_h, start_m, end_h, end_m = time_match.groups()
                        optimal_start = f"{int(start_h):02d}:{start_m}:00"
                        optimal_end = f"{int(end_h):02d}:{end_m}:00"
                        
                        # Check if timing needs to change
                        if optimal_start != session['start_time'] or optimal_end != session['end_time']:
                            print(f"🔄 AI UPDATING: {session['start_time'][:5]}-{session['end_time'][:5]} → {optimal_start[:5]}-{optimal_end[:5]}")
                            
                            # Update session timing
                            supabase.table("sessions").update({
                                "start_time": optimal_start,
                                "end_time": optimal_end,
                                "total_students": new_total
                            }).eq("id", session_id).execute()
                            
                            return f"🤖 DYNAMIC AI SUCCESS: Added {student_id} and UPDATED session to {optimal_start[:5]}-{optimal_end[:5]} based on ALL {new_total} students! 🎯 AI optimized for majority!"
                        else:
                            # Just update student count
                            supabase.table("sessions").update({"total_students": new_total}).eq("id", session_id).execute()
                            
                            return f"✅ Perfect! You're enrolled in the {current_timing} session. {new_total} students total."
                            
                except Exception as e:
                    print(f"⚠️ AI analysis failed: {e}")
            
            # Fallback: Just add student without timing change
            supabase.table("sessions").update({"total_students": new_total}).eq("id", session_id).execute()
            return f"✅ Added {student_id} to existing {subject} session at {current_timing}. Now {new_total} students enrolled!"
        
        else:
            # NO SESSION EXISTS - Create new session for first student
            print(f"🚀 NO EXISTING SESSION - Creating new session for FIRST student: {student_id}")
            
            # Check for duplicate enrollment
            existing_enrollment = supabase.table("student_availability").select("*").eq("student_id", student_id).eq("subject", subject).eq("date", date).execute()
            
            if existing_enrollment.data:
                return f"You already have a {subject.title()} session scheduled for {date}."
            
            # Store student availability
            availability_data = {
                "student_id": student_id,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "subject": subject,
                "session_id": None  # Will be updated after session creation
            }
            supabase.table("student_availability").insert(availability_data).execute()
            
            # Create session
            session_data = {
                "teacher_id": TEACHER_ID,
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
            
            # Enroll student
            supabase.table("session_enrollments").insert({
                "session_id": session_id,
                "student_id": student_id
            }).execute()
            
            # Update availability with session_id
            supabase.table("student_availability").update({"session_id": session_id}).eq("student_id", student_id).eq("date", date).eq("subject", subject).execute()
            
            print(f"✅ CREATED SESSION {session_id} for FIRST student")
            
            return f"✅ Great! {subject.title()} session created for {start_time[:5]}-{end_time[:5]}. You're enrolled!"
        
    except Exception as e:
        print(f"❌ Smart handler error: {e}")
        return f"🤖 Smart handler encountered an error: {e}"

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
            "message": f"Teacher busy at {start_time[:5]}-{end_time[:5]}. Available: {', '.join(teacher_times)}"
        })
        
    except Exception as e:
        return json.dumps({
            "available": False,
            "message": f"Error checking teacher availability: {e}"
        })

def get_teacher_sessions_with_filter(teacher_id: str, filter_type: str = "all") -> list:
    """Get all sessions for a teacher with optional filtering"""
    try:
        print(f"🔍 Getting sessions for teacher {teacher_id} with filter {filter_type}")
        
        # Get all sessions for the teacher
        sessions = supabase.table('sessions').select('*').eq('teacher_id', teacher_id).order('date', {'ascending': True}).execute()
        
        if not sessions.data:
            print(f"No sessions found for teacher {teacher_id}")
            return []
        
        # Apply filtering based on filter_type
        from datetime import datetime, date
        today = date.today()
        
        filtered_sessions = []
        for session in sessions.data:
            session_date = datetime.strptime(session['date'], '%Y-%m-%d').date()
            
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
        
        print(f"✅ Found {len(filtered_sessions)} sessions after filtering")
        return filtered_sessions
        
    except Exception as e:
        print(f"❌ Error getting teacher sessions: {e}")
        return []

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
        
        # AI prompt for timing optimization - focus on majority preference
        ai_prompt = f"""
You are an intelligent session scheduler. Analyze these student availability timings for the SAME SUBJECT:

{timing_text}

MAJORITY-BASED SCHEDULING RULES:
1. Count how many students prefer each time slot
2. Select the time slot preferred by the MOST students (majority wins)
3. Only reject if the time gap is extremely large (>6 hours)
4. Prioritize student majority over perfect overlap

DECISION LOGIC:
- Find the most common time preference
- Use that time slot as the session time
- Accept unless gap > 6 hours (extremely inconvenient)

Respond in this format:
DECISION: [ACCEPT/REJECT]
REASONING: [Explain which time slot has majority preference]
RECOMMENDED_TIME: [HH:MM - HH:MM] (only if ACCEPT)
ACCOMMODATED: [number] students will be accommodated
MAJORITY_COUNT: [number] students prefer this time

Examples:
- Clear majority: "DECISION: ACCEPT\nREASONING: 6 students prefer 16:00-17:00 vs 4 students prefer 12:00-13:00. Using majority preference.\nRECOMMENDED_TIME: 16:00 - 17:00\nACCOMMODATED: 10 students\nMAJORITY_COUNT: 6 students"
- Close call: "DECISION: ACCEPT\nREASONING: 5 students prefer 14:00-15:00 vs 4 students prefer 15:00-16:00. Using majority.\nRECOMMENDED_TIME: 14:00 - 15:00\nACCOMMODATED: 9 students\nMAJORITY_COUNT: 5 students"
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
    """🤖 DYNAMIC AI OPTIMIZER: Adds new student and INTELLIGENTLY UPDATES session timing by analyzing ALL enrolled students. Showcases real-time AI adaptation! Input: JSON with session_id, student_id, preferred_start_time, preferred_end_time, subject, date."""
    try:
        data = json.loads(input)
        session_id = data["session_id"]
        student_id = data["student_id"]
        preferred_start = data["preferred_start_time"]
        preferred_end = data["preferred_end_time"]
        subject = data["subject"].lower()
        date = data["date"]
        
        print(f"🤖 DYNAMIC AI OPTIMIZER: Adding {student_id} to session {session_id}")
        
        # Check if already enrolled
        existing = supabase.table("session_enrollments").select("*").eq("session_id", session_id).eq("student_id", student_id).execute()
        
        if existing.data:
            print(f"⚠️ Student already enrolled")
            return f"✅ You're already enrolled in this {subject} session!"
        
        # Get current session info
        current_session = supabase.table("sessions").select("*").eq("id", session_id).execute()
        if not current_session.data:
            return f"❌ Session not found"
        
        session_info = current_session.data[0]
        current_timing = f"{session_info['start_time'][:5]}-{session_info['end_time'][:5]}"
        current_students = session_info['total_students']
        
        print(f"📊 Current session: {current_timing} with {current_students} students")
        
        # 1. Store new student's availability
        availability_data = {
            "student_id": student_id,
            "date": date,
            "start_time": preferred_start,
            "end_time": preferred_end,
            "subject": subject,
            "session_id": session_id
        }
        supabase.table("student_availability").insert(availability_data).execute()
        
        # 2. Enroll new student
        supabase.table("session_enrollments").insert({
            "session_id": session_id,
            "student_id": student_id
        }).execute()
        
        new_total = current_students + 1
        print(f"✅ Enrolled {student_id}. Now {new_total} students total.")
        
        # 3. 🧠 AI EXCELLENCE: Analyze ALL students (previous + new) for optimal timing
        all_students = supabase.table("student_availability").select("*").eq("session_id", session_id).execute()
        
        student_timings = []
        timing_summary = []
        student_list = []
        
        for avail in all_students.data:
            student_timings.append((avail["start_time"], avail["end_time"]))
            timing_summary.append(f"{avail['student_id']}: {avail['start_time'][:5]}-{avail['end_time'][:5]}")
            student_list.append(avail['student_id'])
        
        print(f"🧠 AI analyzing ALL {len(student_timings)} students for optimal timing:")
        for summary in timing_summary:
            print(f"   {summary}")
        
        # 4. 🤖 DYNAMIC AI OPTIMIZATION
        if llm is not None:
            try:
                ai_prompt = f"""
🤖 DYNAMIC AI SESSION OPTIMIZER

SITUATION: Student {student_id} just joined a {subject.upper()} session on {date}.
CURRENT SESSION: {current_timing} with {current_students} previous students
NEW STUDENT PREFERENCE: {preferred_start[:5]}-{preferred_end[:5]}

ALL STUDENT PREFERENCES (including new student):
{chr(10).join(timing_summary)}

TASK: Determine the NEW OPTIMAL timing considering ALL {new_total} students.

ANALYSIS STEPS:
1. Count votes for each time slot
2. Find the MAJORITY preference
3. Recommend the optimal time for ALL students
4. Consider this is DYNAMIC optimization (session timing can change)

RESPOND IN THIS FORMAT:
CURRENT_TIMING: {current_timing}
VOTE_ANALYSIS: [Count votes for each time slot]
NEW_OPTIMAL_TIME: [HH:MM-HH:MM format]
MAJORITY_COUNT: [Number of students preferring optimal time]
CHANGE_REASON: [Why timing changed or stayed same]
TOTAL_STUDENTS: {new_total}

Example:
CURRENT_TIMING: 12:00-13:00
VOTE_ANALYSIS: 12:00-13:00 has 3 votes, 16:00-17:00 has 4 votes
NEW_OPTIMAL_TIME: 16:00-17:00
MAJORITY_COUNT: 4
CHANGE_REASON: Timing updated because 4 students prefer 16:00-17:00 vs 3 for 12:00-13:00
TOTAL_STUDENTS: 7
"""
                
                ai_response = llm.invoke(ai_prompt)
                ai_decision = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
                print(f"🤖 DYNAMIC AI ANALYSIS:\n{ai_decision}")
                
                # Extract new optimal timing
                import re
                time_match = re.search(r'NEW_OPTIMAL_TIME:\s*(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', ai_decision)
                if time_match:
                    start_h, start_m, end_h, end_m = time_match.groups()
                    new_optimal_start = f"{int(start_h):02d}:{start_m}:00"
                    new_optimal_end = f"{int(end_h):02d}:{end_m}:00"
                    
                    # Check if timing needs to change
                    if new_optimal_start != session_info['start_time'] or new_optimal_end != session_info['end_time']:
                        print(f"🔄 AI UPDATING session timing: {session_info['start_time'][:5]}-{session_info['end_time'][:5]} → {new_optimal_start[:5]}-{new_optimal_end[:5]}")
                        
                        # Update session timing
                        supabase.table("sessions").update({
                            "start_time": new_optimal_start,
                            "end_time": new_optimal_end,
                            "total_students": new_total
                        }).eq("id", session_id).execute()
                        
                        return f"🤖 DYNAMIC AI SUCCESS: Added {student_id} and UPDATED session timing to {new_optimal_start[:5]}-{new_optimal_end[:5]} based on ALL {new_total} students' preferences! 🎯 AI optimized for majority!"
                    else:
                        print(f"✅ AI determined current timing {current_timing} is still optimal")
                        
                        # Just update student count
                        supabase.table("sessions").update({
                            "total_students": new_total
                        }).eq("id", session_id).execute()
                        
                        return f"✅ You're enrolled! Session time: {current_timing}. {new_total} students joined."
                else:
                    # Fallback to algorithmic approach
                    optimal_start, optimal_end = calculate_optimal_timing(student_timings)
                    
                    if optimal_start != session_info['start_time'] or optimal_end != session_info['end_time']:
                        supabase.table("sessions").update({
                            "start_time": optimal_start,
                            "end_time": optimal_end,
                            "total_students": new_total
                        }).eq("id", session_id).execute()
                        
                        return f"✅ Enrolled! Session time updated to {optimal_start[:5]}-{optimal_end[:5]} for all {new_total} students."
                    else:
                        supabase.table("sessions").update({"total_students": new_total}).eq("id", session_id).execute()
                        return f"✅ You're in! Session: {current_timing}. {new_total} students enrolled."
                        
            except Exception as e:
                print(f"⚠️ AI optimization failed: {e}")
                # Just add student without timing change
                supabase.table("sessions").update({"total_students": new_total}).eq("id", session_id).execute()
                return f"✅ Added {student_id} to session. Current timing maintained."
        else:
            # No AI available, use algorithmic approach
            optimal_start, optimal_end = calculate_optimal_timing(student_timings)
            
            if optimal_start != session_info['start_time'] or optimal_end != session_info['end_time']:
                supabase.table("sessions").update({
                    "start_time": optimal_start,
                    "end_time": optimal_end,
                    "total_students": new_total
                }).eq("id", session_id).execute()
                
                return f"🤖 Updated session timing to {optimal_start[:5]}-{optimal_end[:5]} for {new_total} students!"
            else:
                supabase.table("sessions").update({"total_students": new_total}).eq("id", session_id).execute()
                return f"✅ Added {student_id}. Timing remains optimal for {new_total} students!"
        
    except Exception as e:
        print(f"❌ Dynamic AI update error: {e}")
        return f"🤖 Dynamic AI encountered an error: {e}"
        
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
            print(f"🗓️ Teacher parsed day: {list(day_patterns[target_day])[0].title()} → {date}")
        elif "tomorrow" in message_lower:
            date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Teacher parsed: Tomorrow → {date}")
        elif "today" in message_lower:
            date = today.strftime('%Y-%m-%d')
            print(f"🗓️ Teacher parsed: Today → {date}")
        else:
            # Default to tomorrow if no specific date mentioned
            date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            print(f"🗓️ Teacher default: Tomorrow → {date}")
        
        result = {
            "teacher_id": teacher_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "parsed_message": f"Teacher {teacher_id} available on {date} from {start_time[:5]} to {end_time[:5]}"
        }
        
        print(f"✅ Parsed teacher availability: {result['parsed_message']}")
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
        
        # Verify this is the authorized teacher
        if teacher_id != TEACHER_ID:
            print(f"❌ Teacher ID {teacher_id} is not authorized")
            return "❌ Error: You must be the registered teacher to set availability"
        
        print(f"✅ Teacher verified: {teacher_id}")
        
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
            print(f"✅ Updated teacher availability for {date}")
            return f"✅ Availability updated: {start_time[:5]}-{end_time[:5]}"
        else:
            # Insert new availability
            supabase.table("teacher_availability").insert(availability_data).execute()
            print(f"✅ Added teacher availability for {date}")
            return f"✅ Availability set: {start_time[:5]}-{end_time[:5]}"
            
    except Exception as e:
        print(f"❌ Error setting teacher availability: {e}")
        return f"❌ Error setting availability: {e}"

# Tools list - AI-powered tools
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
        from langchain_core.messages import SystemMessage
        
        # Create the agent with tools and system message
        agent = create_react_agent(
            llm, 
            tools, 
            state_modifier=SystemMessage(content=system_prompt)
        )
        
        print("✅ LangGraph agent created successfully")
        graph = agent  # The create_react_agent returns a compiled graph
    except Exception as e:
        print(f"❌ Error creating LangGraph agent: {e}")
        import traceback
        traceback.print_exc()
        graph = None
else:
    graph = None
    print("⚠️ LangGraph agent not created - using mock responses")

# Test function
if __name__ == "__main__":
    print("🧪 Testing improved AI session agent...")
    
    # Test student requests
    print("\n--- Testing Student Requests ---")
    result1 = run_session_agent("Student test123: I want to learn langchain and I'm available 2-3 PM on Friday")
    print(f"Student Result: {result1}")
    
    result2 = run_session_agent("Student test456: I want AWS session from 1-3pm on Saturday")  
    print(f"Student Result: {result2}")
    
    # Test teacher availability (only works with correct teacher ID)
    print("\n--- Testing Teacher Availability ---")
    result3 = run_session_agent("Teacher e4bcab2f-8da5-4a78-85e8-094f4d7ac308: I'm available from 12-4 PM on Saturday")
    print(f"Teacher Result: {result3}")