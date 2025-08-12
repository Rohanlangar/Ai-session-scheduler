#!/usr/bin/env python3
"""
Auth helper to properly set user metadata using Supabase Admin API
"""

from supabase import create_client, Client
import os

# You'll need to get your service role key from Supabase Dashboard > Settings > API
# This is different from the anon key - it has admin privileges
SERVICE_ROLE_KEY = "your_service_role_key_here"  # Replace with actual service role key

def create_admin_client():
    """Create Supabase client with admin privileges"""
    return create_client(
        "https://ipfzpnxdtackprxforqh.supabase.co",
        SERVICE_ROLE_KEY  # Service role key, not anon key
    )

def update_user_metadata(user_id: str, is_teacher: bool):
    """Update user metadata with proper role"""
    try:
        admin_supabase = create_admin_client()
        
        # Update user metadata
        response = admin_supabase.auth.admin.update_user_by_id(
            user_id,
            {
                "user_metadata": {
                    "is_super_admin": is_teacher,
                    "role": "teacher" if is_teacher else "student"
                }
            }
        )
        
        print(f"✅ Updated user {user_id} - is_super_admin: {is_teacher}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating user {user_id}: {e}")
        return False

def fix_all_teacher_roles():
    """Fix roles for all users in teachers table"""
    try:
        # Use regular client to get teachers
        regular_supabase = create_client(
            "https://ipfzpnxdtackprxforqh.supabase.co", 
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k"
        )
        
        teachers = regular_supabase.table('teachers').select('*').execute()
        
        print(f"Found {len(teachers.data)} teachers to update:")
        
        for teacher in teachers.data:
            print(f"Updating {teacher['name']} ({teacher['email']})...")
            update_user_metadata(teacher['id'], True)
            
        print("✅ All teacher roles updated!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Auth Helper - Fixing User Roles")
    print("="*50)
    
    if SERVICE_ROLE_KEY == "your_service_role_key_here":
        print("❌ Please update SERVICE_ROLE_KEY in this file first!")
        print("1. Go to Supabase Dashboard > Settings > API")
        print("2. Copy the 'service_role' key (not anon key)")
        print("3. Replace SERVICE_ROLE_KEY in this file")
    else:
        fix_all_teacher_roles()