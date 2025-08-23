from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from datetime import datetime
import hashlib
import json

app = FastAPI(title="AI Session Scheduler API")

# Simple in-memory cache for responses
response_cache = {}
CACHE_TTL = 300  # 5 minutes

def get_cache_key(user_id: str, message: str) -> str:
    """Generate cache key for user message"""
    return hashlib.md5(f"{user_id}:{message.lower()}".encode()).hexdigest()

def is_cacheable_request(message: str) -> bool:
    """Check if request can be cached (simple patterns)"""
    simple_patterns = [
        "hello", "hi", "help", "what can you do", "available times",
        "schedule", "book session", "cancel", "reschedule"
    ]
    return any(pattern in message.lower() for pattern in simple_patterns)

# Keep-alive mechanism to prevent Render container sleep
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive_task())

async def keep_alive_task():
    """Ping self every 10 minutes to prevent container sleep"""
    import httpx
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            async with httpx.AsyncClient() as client:
                await client.get("http://localhost:8000/api/health", timeout=5)
            print(f"🔄 Keep-alive ping at {datetime.now()}")
        except Exception as e:
            print(f"⚠️ Keep-alive failed: {e}")

# CORS - Allow frontend to connect
import os

# CORS - Allow frontend to connect
allowed_origins = [
    "https://ai-session-scheduler-vr6n.vercel.app",
    "http://localhost:3000",
    "http://localhost:8000"
]

# Add CORS_ORIGINS from environment if available
cors_origins_env = os.getenv("CORS_ORIGINS")
if cors_origins_env:
    allowed_origins.extend(cors_origins_env.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    user_id: str
    is_teacher: bool = False

class TeacherSessionsRequest(BaseModel):
    teacher_id: str
    filter_type: str = "all"  # "all", "today_future", "today", "future"

@app.post("/api/chat-session")
async def chat_session(request: ChatRequest):
    """Handle chat messages and create sessions"""
    try:
        # Check cache for simple requests
        cache_key = get_cache_key(request.user_id, request.message)
        if is_cacheable_request(request.message) and cache_key in response_cache:
            cached_response = response_cache[cache_key]
            if datetime.now().timestamp() - cached_response["timestamp"] < CACHE_TTL:
                print(f"🚀 Cache hit for: {request.message[:30]}...")
                return cached_response["response"]
        
        # Lazy import to reduce startup time
        from tools import run_session_agent
        
        # Format message for the agent
        if request.is_teacher:
            user_message = f"Teacher {request.user_id}: {request.message}"
        else:
            user_message = f"Student {request.user_id}: {request.message}"
        
        # Get AI response
        response = run_session_agent(user_message)
        
        result = {
            "success": True,
            "response": response,
            "user_id": request.user_id,
            "is_teacher": request.is_teacher
        }
        
        # Cache simple responses
        if is_cacheable_request(request.message):
            response_cache[cache_key] = {
                "response": result,
                "timestamp": datetime.now().timestamp()
            }
        
        return result
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return {
            "success": False,
            "response": "✅ I understand! Let me help you.",
            "user_id": request.user_id,
            "is_teacher": request.is_teacher
        }

@app.post("/api/teacher-sessions")
async def get_teacher_sessions(request: TeacherSessionsRequest):
    """Get all sessions for a teacher with optional filtering"""
    try:
        from tools import get_teacher_sessions_with_filter
        
        sessions = get_teacher_sessions_with_filter(request.teacher_id, request.filter_type)
        
        return {
            "success": True,
            "sessions": sessions,
            "teacher_id": request.teacher_id,
            "filter_type": request.filter_type
        }
        
    except Exception as e:
        print(f"❌ API Error getting teacher sessions: {e}")
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "message": "AI Session Scheduler API is running"}

@app.get("/")
async def root():
    return {"message": "AI Session Scheduler API", "status": "running"}

if __name__ == "__main__":
    print("🚀 Starting AI Session Scheduler...")
    print("📡 Backend: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "api_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )