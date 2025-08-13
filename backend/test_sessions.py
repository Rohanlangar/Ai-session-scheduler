from tools import supabase

# Check current sessions
sessions = supabase.table('sessions').select('*').eq('status', 'active').execute()
print(f"Active sessions: {len(sessions.data)}")

for s in sessions.data:
    print(f"- {s['subject']} on {s['date']} at {s['start_time']}-{s['end_time']} (ID: {s['id']})")