# AI Session Scheduler

A chat-focused AI session scheduler with Supabase authentication and role-based access.

## ✨ New Features

- **🔐 Supabase Authentication** - Login/Signup with Google OAuth
- **💬 70% Chat Interface** - Natural conversation for scheduling
- **📅 30% Sessions Sidebar** - View your sessions
- **👥 Role-based Access** - Teachers vs Students (using `is_super_admin` field)
- **🎨 Fixed UI** - Black text in input fields

## Project Structure

```
├── backend/           # Python backend
│   ├── tools.py      # AI session scheduling logic
│   ├── api_server.py # Flask API server
│   └── requirements.txt
└── frontend/         # Next.js frontend
    ├── src/
    │   ├── app/
    │   ├── components/
    │   │   ├── AuthForm.tsx      # Login/Signup
    │   │   └── ChatInterface.tsx # Main chat UI
    │   ├── lib/
    │   └── types/
    └── package.json
```

## 🚀 Setup Instructions

### 1. Supabase Configuration

In your Supabase dashboard:

1. **Enable Google OAuth:**
   - Go to Authentication > Providers
   - Enable Google provider
   - Add your Google OAuth credentials

2. **User Role Detection:**
   - Uses existing `is_super_admin` field in auth.users
   - `is_super_admin = true` → Teacher
   - `is_super_admin = false` → Student

### 2. Fix User Roles (One-time setup)

If you have existing users who registered as teachers but don't have `is_super_admin=true`:

```bash
cd backend
python fix_user_roles.py
```

Then manually update the users in Supabase Dashboard as instructed.

### 3. Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirement.txt
python api_server.py
```

**FastAPI Backend** runs on `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

## 🎯 How It Works

### Authentication Flow
1. User selects "Teacher" or "Student"
2. Login/Signup with email or Google
3. Role stored in `user_metadata.is_super_admin`
4. Automatic redirect to chat interface

### Chat Interface (70% of screen)
- **Teachers**: "I'm available Monday 2-4 PM for Python sessions"
- **Students**: "I'm free Monday 2-4 PM for Python"
- **AI Agent**: Processes natural language and manages sessions

### Sessions Sidebar (30% of screen)
- **Teachers**: View all their scheduled sessions
- **Students**: View enrolled sessions with meeting links

### User ID Integration
- Authenticated user ID automatically used in session data
- No manual user selection needed
- Secure role-based access

## 🔧 API Endpoints

- `POST /api/chat-session` - Handle chat messages
- `GET /api/health` - Health check

## 💾 Database Integration

- **auth.users** - Authentication with `is_super_admin` role
- **teachers/students** - Profile data linked to auth.users.id
- **sessions** - Created with authenticated user IDs
- **session_enrollments** - Links students to sessions

## 🎨 UI Improvements

- ✅ Fixed black text in input fields
- ✅ Chat-focused layout (70/30 split)
- ✅ Proper authentication flow
- ✅ Role-based interface differences
- ✅ Google OAuth integration

## 🚀 Usage

1. Open `http://localhost:3000`
2. Choose your role (Teacher/Student)
3. Login with email or Google
4. Start chatting about your availability!

**Example Messages:**
- "I'm available tomorrow 3-5 PM for JavaScript"
- "Can I join a Python session on Friday?"
- "I teach React from 2-4 PM on weekdays"