@echo off
echo 🚀 Starting AI Session Scheduler...

echo 📡 Starting Backend...
cd backend
start "Backend" cmd /k "python api_server.py"

echo ⏳ Waiting 3 seconds...
timeout /t 3 /nobreak > nul

echo 🌐 Starting Frontend...
cd ../frontend
start "Frontend" cmd /k "npm run dev"

echo ✅ Both servers starting!
echo 📡 Backend: http://localhost:8000
echo 🌐 Frontend: http://localhost:3000
pause