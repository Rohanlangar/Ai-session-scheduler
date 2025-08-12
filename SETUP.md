# Setup Instructions

## Environment Variables Setup

1. **Backend Setup:**
   ```bash
   cd backend
   cp .env.example .env
   ```

2. **Edit backend/.env with your actual keys:**
   ```
   SUPABASE_URL=https://ipfzpnxdtackprxforqh.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k
   OPENAI_API_KEY=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
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   ```
   
   Create `.env.local`:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://ipfzpnxdtackprxforqh.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZnpwbnhkdGFja3ByeGZvcnFoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQzMDA1NTYsImV4cCI6MjA2OTg3NjU1Nn0.LXfpdquRCyv3QZAYDFxZmM6FNOcl24IDRUTMfvlGh5k
   ```

## Installation & Running

1. **Backend:**
   ```bash
   cd backend
   pip install -r requirement.txt
   python api_server.py
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Important Notes

- Never commit .env files to git
- The .env files contain sensitive API keys
- Use .env.example as a template