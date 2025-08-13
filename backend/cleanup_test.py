from tools import supabase

# Clean up test sessions
print("🧹 Cleaning up test sessions...")

# Delete test sessions
sessions = supabase.table('sessions').select('*').eq('status', 'active').execute()
for session in sessions.data:
    if session['date'] == '2025-08-13':
        print(f"Deleting session: {session['subject']} on {session['date']}")
        # Delete enrollments first
        supabase.table('session_enrollments').delete().eq('session_id', session['id']).execute()
        # Delete availability records
        supabase.table('student_availability').delete().eq('session_id', session['id']).execute()
        # Delete session
        supabase.table('sessions').delete().eq('id', session['id']).execute()

print("✅ Cleanup complete!")