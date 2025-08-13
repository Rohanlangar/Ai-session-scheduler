# Deployment Instructions

## For GitHub/Production Deployment

### Option 1: Use Clean Version (Recommended)
1. Replace `backend/tools.py` with `backend/tools_clean.py` content
2. This version has no hardcoded secrets and requires proper .env setup
3. Commit and push to GitHub safely

### Option 2: Manual Cleanup
1. Remove hardcoded fallback values from `backend/tools.py`
2. Keep only the environment variable loading code
3. Ensure all secrets come from .env files

## Environment Variables Setup

### Development
- Use `backend/.env` and `frontend/.env` files
- Copy from `.env.example` files
- Never commit these files

### Production (Render/Vercel/etc.)
Set these environment variables in your deployment platform:

**Backend:**
- `SUPABASE_URL`
- `SUPABASE_KEY` 
- `ANTHROPIC_API_KEY`

**Frontend:**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_BACKEND_URL`

## Security Checklist
- [ ] No hardcoded API keys in code
- [ ] All .env files in .gitignore
- [ ] .env.example files created
- [ ] Environment variables set in production
- [ ] Secrets properly validated on startup