# Fast response patterns for common requests
import re
from datetime import datetime, timedelta

def get_fast_response(message: str, user_id: str, is_teacher: bool) -> str:
    """Return fast responses for common patterns without AI processing"""
    message_lower = message.lower().strip()
    
    # Common greetings
    if any(word in message_lower for word in ["hello", "hi", "hey"]):
        if is_teacher:
            return "Hi! Ready to set your availability? Just tell me the day and time."
        else:
            return "Hi! I can help you book a session. What subject and when?"
    
    # Help requests
    if any(word in message_lower for word in ["help", "what can you do"]):
        if is_teacher:
            return "I help you set teaching availability. Say something like 'Available Monday 2-3pm'"
        else:
            return "I help book sessions. Say something like 'Python session tomorrow 2-3pm'"
    
    # Status requests
    if any(word in message_lower for word in ["status", "sessions", "schedule"]):
        return "Let me check your current sessions..."
    
    # Simple time patterns for quick booking
    time_pattern = r'(\d{1,2})\s*-\s*(\d{1,2})\s*(pm|am)'
    if re.search(time_pattern, message_lower):
        # Extract subject
        subjects = ["python", "react", "java", "javascript", "web", "mobile", "devops"]
        found_subject = next((s for s in subjects if s in message_lower), "python")
        
        if is_teacher:
            return f"Setting availability for {found_subject}..."
        else:
            return f"Booking {found_subject} session..."
    
    return None  # No fast response available

def is_simple_request(message: str) -> bool:
    """Check if request can be handled with simple pattern matching"""
    simple_patterns = [
        r'hello|hi|hey',
        r'help|what can you do',
        r'available.*\d+.*pm|am',
        r'book.*\d+.*pm|am',
        r'schedule.*\d+.*pm|am'
    ]
    
    message_lower = message.lower()
    return any(re.search(pattern, message_lower) for pattern in simple_patterns)