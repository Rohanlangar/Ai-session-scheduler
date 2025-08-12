# Deployment Guide

## Backend Deployment on Render

### Step 1: Prepare Your Repository
1. Make sure all API keys are removed from code
2. Push your code to GitHub (without API keys)

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `ai-session-scheduler-backend`
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main` (or your preferred branch)
- **Root Directory**: `backend`

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python api_server.py`

**Environment Variables:**
Add these in Render dashboard:
- `SUPABASE_URL` = your Supabase project URL
- `SUPABASE_KEY` = your Supabase anon key  
- `OPENAI_API_KEY` = your OpenAI API key
- `PYTHON_VERSION` = `3.11.0`

### Step 3: Get Your Backend URL
After deployment, Render will give you a URL like:
`https://ai-session-scheduler-backend.onrender.com`

## Frontend Deployment on Vercel

### Step 1: Update Frontend Environment
1. Update `frontend/.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
NEXT_PUBLIC_BACKEND_URL=https://your-render-backend-url.onrender.com
```

### Step 2: Deploy on Vercel
1. Go to [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Set root directory to `frontend`
4. Add environment variables in Vercel dashboard
5. Deploy!

## Important Notes

- **Backend URL**: Update frontend to use your Render backend URL
- **CORS**: Already configured for Vercel domains
- **Environment Variables**: Set them in respective platforms (Render/Vercel)
- **Database**: Supabase works from anywhere (no changes needed)

## Testing Deployment

1. **Backend Health Check**: Visit `https://your-backend.onrender.com/api/health`
2. **API Documentation**: Visit `https://your-backend.onrender.com/docs`
3. **Frontend**: Should connect to deployed backend automatically

## Troubleshooting

- **CORS Issues**: Check if frontend URL is in CORS origins
- **Environment Variables**: Verify all keys are set correctly
- **Build Failures**: Check logs in Render/Vercel dashboards