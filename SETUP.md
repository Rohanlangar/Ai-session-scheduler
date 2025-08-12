# Setup Instructions

## Environment Variables Setup

1. **Backend Setup:**
   ```bash
   cd backend
   cp .env.example .env
   ```

2. **Edit backend/.env with your actual keys:**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_anon_key_here
   OPENAI_API_KEY=sk-proj-your_openai_api_key_here
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   ```
   
   Create `.env.local`:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key_here
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