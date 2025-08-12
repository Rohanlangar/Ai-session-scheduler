#!/usr/bin/env python3
"""
Script to fix user roles in Supabase for existing users
Run this to update is_super_admin field for users who registered as teachers
"""

from supabase import create_client, Client
import os

# Supabase Setup
supabase: Client = create_client(
    "https://ipfzpnxdtackprxforqh.supabase.co", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k"
)

def fix_teacher_roles():
    """Update is_super_admin for users who are in the teachers table"""
    try:
        # Get all teachers
        teachers_response = supabase.table('teachers').select('*').execute()
        teachers = teachers_response.data
        
        print(f"Found {len(teachers)} teachers in database:")
        
        for teacher in teachers:
            teacher_id = teacher.get('id', 'N/A')
            teacher_name = teacher.get('name', 'N/A')
            print(f"- Teacher ID: {teacher_id}")
            print(f"  Name: {teacher_name}")
            print(f"  Fields: {list(teacher.keys())}")
            
            # Note: We cannot directly update auth.users table from client
            # This needs to be done through Supabase admin API or dashboard
            print(f"  → Please manually set is_super_admin=true for user ID: {teacher_id}")
        
        print("\n" + "="*60)
        print("MANUAL STEPS REQUIRED:")
        print("1. Go to your Supabase Dashboard")
        print("2. Navigate to Authentication > Users")
        print("3. For each teacher ID listed above:")
        print("   - Click on the user")
        print("   - Go to 'Raw User Meta Data'")
        print("   - Add/Update: \"is_super_admin\": true")
        print("   - Save changes")
        print("="*60)
        
    except Exception as e:
        print(f"Error: {e}")

def check_user_roles():
    """Check current user roles (this won't show auth metadata, just table data)"""
    try:
        teachers = supabase.table('teachers').select('*').execute()
        students = supabase.table('students').select('*').execute()
        
        print("CURRENT DATABASE STATE:")
        print(f"Teachers: {len(teachers.data)}")
        for teacher in teachers.data:
            print(f"  - Teacher ID: {teacher.get('id', 'N/A')}")
            print(f"    Fields: {list(teacher.keys())}")
            
        print(f"Students: {len(students.data)}")
        for student in students.data:
            print(f"  - Student ID: {student.get('id', 'N/A')}")
            print(f"    Fields: {list(student.keys())}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🔧 Fixing User Roles in Supabase...")
    print("="*50)
    
    check_user_roles()
    print()
    fix_teacher_roles()