from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tools import run_session_agent
import uvicorn
from typing import Optional

app = FastAPI(title="AI Session Scheduler API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request validation
class ChatSessionRequest(BaseModel):
    message: str
    user_id: str
    is_teacher: bool = False

class SessionRequest(BaseModel):
    student_id: str
    subject: str
    date: str
    start_time: str
    end_time: str

class ChatSessionResponse(BaseModel):
    success: bool
    response: str
    user_id: str
    is_teacher: bool
    error: Optional[str] = None

class SessionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None

@app.post("/api/chat-session", response_model=ChatSessionResponse)
async def handle_chat_session(request: ChatSessionRequest):
    try:
        # Add user context to the message
        if request.is_teacher:
            contextual_message = f"Teacher {request.user_id}: {request.message}"
        else:
            contextual_message = f"Student {request.user_id}: {request.message}"
        
        # Run your session agent
        result = run_session_agent(contextual_message)
        
        return ChatSessionResponse(
            success=True,
            response=result,
            user_id=request.user_id,
            is_teacher=request.is_teacher
        )
        
    except Exception as e:
        return ChatSessionResponse(
            success=False,
            response='I understand your request. Let me process that for you.',
            user_id=request.user_id,
            is_teacher=request.is_teacher,
            error=str(e)
        )

@app.post("/api/session-request", response_model=SessionResponse)
async def handle_session_request(request: SessionRequest):
    try:
        # Format the request for your AI agent
        user_input = f"Student {request.student_id}: I am available on {request.date} from {request.start_time} to {request.end_time} for {request.subject} session"
        
        # Run your session agent
        result = run_session_agent(user_input)
        
        return SessionResponse(
            success=True,
            message=result,
            data={
                'student_id': request.student_id,
                'subject': request.subject,
                'date': request.date,
                'start_time': request.start_time,
                'end_time': request.end_time
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "AI Session Scheduler API", "version": "1.0.0"}

if __name__ == '__main__':
    print("🚀 Starting AI Session Scheduler FastAPI Server...")
    print("📡 Server running on http://localhost:8001")
    print("📖 API Documentation: http://localhost:8001/docs")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8001, reload=True)