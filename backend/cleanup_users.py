#!/usr/bin/env python3
"""
Script to clean up duplicate users and fix role conflicts
"""

from supabase import create_client, Client
import json

# Supabase Setup
supabase: Client = create_client(
    "https://ipfzpnxdtackprxforqh.supabase.co", 
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k"
)

def find_duplicate_users():
    """Find users who exist in both teachers and students tables"""
    try:
        teachers = supabase.table('teachers').select('*').execute()
        students = supabase.table('students').select('*').execute()
        
        teacher_user_ids = {t['user_id'] for t in teachers.data}
        student_user_ids = {s['user_id'] for s in students.data}
        
        duplicates = teacher_user_ids.intersection(student_user_ids)
        
        print(f"Found {len(duplicates)} duplicate users:")
        for user_id in duplicates:
            teacher_data = next(t for t in teachers.data if t['user_id'] == user_id)
            student_data = next(s for s in students.data if s['user_id'] == user_id)
            
            print(f"\nUser ID: {user_id}")
            print(f"  Teacher entry: {teacher_data}")
            print(f"  Student entry: {student_data}")
            
        return duplicates, teachers.data, students.data
        
    except Exception as e:
        print(f"Error finding duplicates: {e}")
        return set(), [], []

def cleanup_duplicates():
    """Interactive cleanup of duplicate users"""
    duplicates, teachers, students = find_duplicate_users()
    
    if not duplicates:
        print("✅ No duplicate users found!")
        return
    
    print("\n" + "="*60)
    print("CLEANUP OPTIONS:")
    print("1. Remove all duplicates from students table (keep as teachers)")
    print("2. Remove all duplicates from teachers table (keep as students)")
    print("3. Manual cleanup (choose for each user)")
    print("4. Exit without changes")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        # Remove from students table
        for user_id in duplicates:
            try:
                supabase.table('students').delete().eq('user_id', user_id).execute()
                print(f"✅ Removed {user_id} from students table")
            except Exception as e:
                print(f"❌ Error removing {user_id} from students: {e}")
                
    elif choice == '2':
        # Remove from teachers table
        for user_id in duplicates:
            try:
                supabase.table('teachers').delete().eq('user_id', user_id).execute()
                print(f"✅ Removed {user_id} from teachers table")
            except Exception as e:
                print(f"❌ Error removing {user_id} from teachers: {e}")
                
    elif choice == '3':
        # Manual cleanup
        for user_id in duplicates:
            teacher_data = next(t for t in teachers if t['user_id'] == user_id)
            student_data = next(s for s in students if s['user_id'] == user_id)
            
            print(f"\nUser: {teacher_data.get('name', 'Unknown')} ({user_id})")
            print("1. Keep as Teacher (remove from students)")
            print("2. Keep as Student (remove from teachers)")
            print("3. Skip this user")
            
            user_choice = input("Choice (1-3): ").strip()
            
            if user_choice == '1':
                try:
                    supabase.table('students').delete().eq('user_id', user_id).execute()
                    print(f"✅ Kept {user_id} as teacher")
                except Exception as e:
                    print(f"❌ Error: {e}")
            elif user_choice == '2':
                try:
                    supabase.table('teachers').delete().eq('user_id', user_id).execute()
                    print(f"✅ Kept {user_id} as student")
                except Exception as e:
                    print(f"❌ Error: {e}")
            else:
                print(f"⏭️ Skipped {user_id}")
    
    else:
        print("Exiting without changes")

def show_current_state():
    """Show current database state"""
    try:
        teachers = supabase.table('teachers').select('*').execute()
        students = supabase.table('students').select('*').execute()
        
        print("CURRENT DATABASE STATE:")
        print(f"Teachers ({len(teachers.data)}):")
        for teacher in teachers.data:
            print(f"  - {teacher.get('name', 'Unknown')} ({teacher['user_id']})")
            
        print(f"\nStudents ({len(students.data)}):")
        for student in students.data:
            print(f"  - {student.get('name', 'Unknown')} ({student['user_id']})")
            
    except Exception as e:
        print(f"Error showing state: {e}")

if __name__ == "__main__":
    print("🧹 User Cleanup Tool")
    print("="*50)
    
    show_current_state()
    print("\n" + "="*50)
    
    cleanup_duplicates()
    
    print("\n" + "="*50)
    print("FINAL STATE:")
    show_current_state()