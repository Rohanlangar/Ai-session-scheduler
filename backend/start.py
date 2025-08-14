#!/usr/bin/env python3
"""
Simple startup script for the AI Session Scheduler backend
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    print("🚀 Starting AI Session Scheduler Backend...")
    print("📡 Backend URL: http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔧 Environment loaded from .env file")
    
    # Check if required environment variables are set
    required_vars = ["SUPABASE_URL", "SUPABASE_KEY", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("   The system will use fallback values, but some features may not work properly.")
    else:
        print("✅ All required environment variables are set")
    
    print("\n" + "="*50)
    print("Backend is starting...")
    print("="*50 + "\n")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )