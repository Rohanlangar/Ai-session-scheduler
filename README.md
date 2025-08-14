# AI Session Scheduler

An intelligent session scheduling system with automatic role assignment and AI-powered session management.

## 🚀 Features

- **Automatic Role Assignment**: Teachers and students are automatically assigned based on user ID
- **AI-Powered Scheduling**: Smart session creation and optimization using Claude AI
- **Real-time Updates**: Live session updates using Supabase subscriptions
- **Teacher Dashboard**: Set availability and manage sessions
- **Student Dashboard**: Book sessions and view enrollments

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python
- **Database**: Supabase (PostgreSQL)
- **AI**: Anthropic Claude via LangChain
- **Authentication**: Supabase Auth

## 📋 Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.8+
- Supabase account
- Anthropic API key

## 🛠️ Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install frontend dependencies
cd frontend
npm install

# Install backend dependencies
cd ../backend
pip install -r requirements.txt
```

### 2. Environment Configuration

**Frontend (.env):**
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

**Backend (.env):**
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 3. Database Setup

The system uses these Supabase tables:
- `users` - User authentication
- `teachers` - Teacher profiles
- `sessions` - Session data
- `session_enrollments` - Student enrollments
- `student_availability` - Student time preferences
- `teacher_availability` - Teacher availability

### 4. Authentication Setup

**Important**: The system has automatic role assignment:
- User ID `e4bcab2f-8da5-4a78-85e8-094f4d7ac308` → **Teacher**
- All other user IDs → **Student**

To disable email confirmation in Supabase:
1. Go to Supabase Dashboard → Authentication → Settings
2. Turn off "Enable email confirmations"
3. Save settings

## 🚀 Running the Application

### Start Backend (Terminal 1)
```bash
cd backend
python start.py
# Or alternatively: python api_server.py
```

### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 💬 How to Use

### For Teachers
1. Login with the designated teacher ID
2. Set availability: "I'm available Friday 2-5 PM for Python sessions"
3. View and manage your sessions in the sidebar

### For Students
1. Login with any other user ID (auto-assigned as student)
2. Request sessions: "I want Python session 2-3 PM"
3. Join sessions via the Meet links in your dashboard

## 🤖 AI Features

The system uses Claude AI to:
- Parse natural language requests
- Create and optimize session timings
- Handle teacher availability setting
- Manage student enrollments intelligently

## 🔧 API Endpoints

- `POST /api/chat-session` - Process chat messages and manage sessions
- `GET /api/health` - Health check
- `GET /` - API status

## 🐛 Troubleshooting

### Common Issues

1. **Backend Connection Error**
   - Ensure backend is running on port 8000
   - Check CORS settings in api_server.py

2. **Authentication Issues**
   - Verify Supabase credentials
   - Check email confirmation settings

3. **AI Not Working**
   - Verify Anthropic API key is valid
   - Check backend logs for errors

### Logs and Debugging

- Backend logs: Check terminal running `python start.py`
- Frontend logs: Check browser console
- Database: Use Supabase dashboard

## 📝 Development Notes

- The system automatically refreshes sessions every 2 seconds for real-time updates
- Teacher availability is stored separately from sessions
- Session timing is optimized based on all enrolled students' preferences
- The AI agent uses LangGraph for structured conversation flow

## 🔒 Security

- All API keys should be kept secure
- Supabase RLS (Row Level Security) should be configured for production
- CORS is configured for development (localhost:3000)

## 📄 License

This project is for educational/demonstration purposes.