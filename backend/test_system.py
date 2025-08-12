#!/usr/bin/env python3

from tools import run_session_agent

def test_student_request():
    print("🧪 Testing Student Session Request...")
    print("=" * 50)
    
    # Test student request
    user_input = "Student abc123: I am available from 2-3 PM for flask on monday"
    result = run_session_agent(user_input)
    
    print("Input:", user_input)
    print("Result:", result)
    print("=" * 50)

def test_teacher_availability():
    print("🧪 Testing Teacher Availability...")
    print("=" * 50)
    
    # Test teacher availability
    user_input = "Teacher teacher123: I am available from 12-4 PM for python on monday"
    result = run_session_agent(user_input)
    
    print("Input:", user_input)
    print("Result:", result)
    print("=" * 50)

if __name__ == "__main__":
    test_student_request()
    test_teacher_availability()