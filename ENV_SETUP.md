# Environment Variables Setup

## Backend Setup

1. Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```

2. Fill in your actual values in `backend/.env`:
```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

## Frontend Setup

1. Copy the example environment file:
```bash
cp frontend/.env.example frontend/.env
```

2. Fill in your actual values in `frontend/.env`:
```env
# Supabase Configuration (Public)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Backend URL
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## Getting Your Keys

### Supabase
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to Settings > API
4. Copy the URL and anon/public key

### Anthropic
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Copy the key (starts with `sk-ant-api03-`)

## Security Notes

- Never commit `.env` files to git
- The `.env` files are already in `.gitignore`
- Use `.env.example` files to show required variables without exposing secrets
- Frontend variables with `NEXT_PUBLIC_` prefix are exposed to the browser