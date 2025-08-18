from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="AI Session Scheduler API")

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
        if request.is_teacher:
            # Handle teacher messages with AI agent for availability
            from tools import run_session_agent
            
            # Format message for the agent (as teacher)
            user_message = f"Teacher {request.user_id}: {request.message}"
            
            # Get AI response
            response = run_session_agent(user_message)
            
            return {
                "success": True,
                "response": response,
                "user_id": request.user_id,
                "is_teacher": request.is_teacher
            }
        else:
            # Handle student session requests with AI
            from tools import run_session_agent
            
            # Format message for the agent
            user_message = f"Student {request.user_id}: {request.message}"
            
            # Get AI response
            response = run_session_agent(user_message)
            
            return {
                "success": True,
                "response": response,
                "user_id": request.user_id,
                "is_teacher": request.is_teacher
            }
        
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