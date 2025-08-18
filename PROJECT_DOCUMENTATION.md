# AI Session Scheduler - Project Documentation

## 📋 Project Overview

The AI Session Scheduler is an intelligent web application that automates the process of scheduling educational sessions between teachers and students. It uses AI to optimize timing conflicts, manage availability, and create sessions based on natural language requests.

## 🌐 Live Application

- **Frontend**: https://ai-session-scheduler-vr6n.vercel.app
- **Backend API**: https://ai-session-scheduler-2.onrender.com
- **API Documentation**: https://ai-session-scheduler-2.onrender.com/docs

## 🏗️ Architecture

### Frontend (Next.js + TypeScript)
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **Authentication**: Supabase Auth
- **Deployment**: Vercel
- **Key Features**:
  - Real-time chat interface
  - Session dashboard
  - Teacher/Student role management
  - Responsive design

### Backend (FastAPI + Python)
- **Framework**: FastAPI
- **AI Integration**: Anthropic Claude (via LangChain)
- **Database**: Supabase (PostgreSQL)
- **Deployment**: Render
- **Key Features**:
  - Natural language processing
  - Intelligent session scheduling
  - Conflict resolution
  - RESTful API endpoints

## 🤖 AI Features

### 1. Natural Language Processing
- **Student Requests**: "I want Python session 2-3 PM on Tuesday"
- **Teacher Availability**: "I'm available Monday 12-5 PM"
- **Subject Mapping**: Automatically maps specific technologies to broad categories
  - Flask/Django → Python
  - React/Next.js → React
  - Spring Boot → Java

### 2. Intelligent Scheduling
- **Conflict Detection**: AI analyzes timing conflicts between students
- **Optimal Timing**: Calculates best session times for multiple students
- **Teacher Availability**: Matches sessions with teacher schedules
- **Automatic Enrollment**: Adds students to existing compatible sessions

### 3. Smart Subject Categorization
- **Broad Categories**: Python, React, Java, JavaScript, Database, Web, Mobile, DevOps
- **Framework Mapping**: Specific frameworks mapped to main subjects
- **Typo Tolerance**: Handles common spelling mistakes in day names

## 📊 Database Schema

### Core Tables
1. **Users**: Student and teacher profiles
2. **Sessions**: Scheduled learning sessions
3. **Session_Enrollments**: Student-session relationships
4. **Teacher_Availability**: Teacher schedule management
5. **Student_Availability**: Student timing preferences

## 🔧 Technical Implementation

### AI Agent Workflow
```
1. Message Processing → Intent Detection (Student/Teacher)
2. Natural Language Parsing → Extract subject, timing, date
3. Conflict Analysis → AI-powered timing optimization
4. Session Management → Create/Update sessions
5. Response Generation → User-friendly confirmations
```

### Key Technologies
- **LangGraph**: AI agent orchestration
- **Anthropic Claude**: Natural language understanding
- **Supabase**: Real-time database and authentication
- **FastAPI**: High-performance API framework
- **Next.js**: Modern React framework

## 🚀 Deployment Architecture

### Production Environment
- **Frontend**: Vercel (Global CDN)
- **Backend**: Render (Cloud hosting)
- **Database**: Supabase (Managed PostgreSQL)
- **AI Service**: Anthropic API

### Environment Configuration
- **CORS**: Configured for cross-origin requests
- **Environment Variables**: Secure credential management
- **SSL**: HTTPS encryption for all communications

## 📈 Key Features Implemented

### For Students
- ✅ Natural language session requests
- ✅ Automatic subject categorization
- ✅ Flexible timing preferences
- ✅ Session enrollment management
- ✅ Real-time chat interface

### For Teachers
- ✅ Availability setting via chat
- ✅ Multi-day schedule management
- ✅ Automatic session assignment
- ✅ Student enrollment tracking

### AI Capabilities
- ✅ Intent recognition (Student vs Teacher)
- ✅ Timing conflict resolution
- ✅ Optimal schedule calculation
- ✅ Natural language understanding
- ✅ Typo tolerance and error handling

## 🔍 System Workflow Examples

### Student Session Request
```
Input: "I want Flask session 2-3 PM on Tuesday"
Processing:
1. Detect: Student intent
2. Parse: Subject=Python, Time=14:00-15:00, Date=2025-08-19
3. Check: Existing Python sessions on 2025-08-19
4. Action: Create new session or enroll in existing
5. Response: "✅ Python session created for Tuesday 2-3 PM"
```

### Teacher Availability
```
Input: "I'm available Monday 12-5 PM"
Processing:
1. Detect: Teacher intent
2. Parse: Date=2025-08-18, Time=12:00-17:00
3. Action: Set teacher availability
4. Response: "✅ Availability set for Monday 12:00-17:00"
```

## 📋 Technical Specifications

### Performance
- **Response Time**: < 2 seconds for AI processing
- **Concurrent Users**: Supports multiple simultaneous requests
- **Scalability**: Cloud-native architecture

### Security
- **Authentication**: Supabase Auth with JWT tokens
- **API Security**: CORS configuration and rate limiting
- **Data Protection**: Environment variable management

### Reliability
- **Error Handling**: Comprehensive exception management
- **Fallback Systems**: Graceful degradation for AI failures
- **Monitoring**: Real-time logging and debugging

## 🎯 Business Value

### Efficiency Gains
- **Automated Scheduling**: Reduces manual coordination time
- **Conflict Resolution**: AI prevents scheduling conflicts
- **Natural Interface**: No complex forms or interfaces needed

### User Experience
- **Conversational**: Chat-based interaction
- **Intelligent**: Context-aware responses
- **Flexible**: Handles various input formats and typos

### Scalability
- **Multi-Subject**: Supports various programming languages
- **Multi-User**: Handles multiple teachers and students
- **Extensible**: Easy to add new subjects and features

## 🔮 Future Enhancements

### Planned Features
- **Calendar Integration**: Google Calendar sync
- **Video Conferencing**: Integrated meeting links
- **Progress Tracking**: Student learning analytics
- **Mobile App**: Native mobile applications
- **Multi-Language**: Support for multiple languages

### Technical Improvements
- **Advanced AI**: More sophisticated scheduling algorithms
- **Real-time Updates**: WebSocket integration
- **Caching**: Redis for improved performance
- **Analytics**: Comprehensive usage analytics

## 📞 Support & Maintenance

### Monitoring
- **Health Checks**: Automated system monitoring
- **Error Tracking**: Comprehensive logging system
- **Performance Metrics**: Response time and usage analytics

### Updates
- **Continuous Deployment**: Automated deployment pipeline
- **Version Control**: Git-based development workflow
- **Testing**: Automated testing for reliability

---

**Project Status**: ✅ Production Ready
**Last Updated**: August 2025
**Version**: 1.0.0
## 🤖 AI Ag
ent Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AI SESSION SCHEDULER AGENT                            │
│                         (Anthropic Claude + LangGraph)                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT PROCESSING                              │
│  • Extract user ID from message format                                         │
│  • Clean message content                                                       │
│  • Detect intent (Student vs Teacher)                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────┐
                              │  INTENT ROUTER  │
                              └─────────────────┘
                                        │
                        ┌───────────────┼───────────────┐
                        ▼                               ▼
            ┌─────────────────────┐           ┌─────────────────────┐
            │   STUDENT WORKFLOW  │           │  TEACHER WORKFLOW   │
            └─────────────────────┘           └─────────────────────┘
                        │                               │
                        ▼                               ▼
        ┌─────────────────────────────┐     ┌─────────────────────────────┐
        │     STUDENT TOOLS CHAIN     │     │     TEACHER TOOLS CHAIN     │
        └─────────────────────────────┘     └─────────────────────────────┘
                        │                               │
                        ▼                               ▼
    ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
    │    1. parse_student_request     │   │  1. parse_teacher_availability  │
    │    ├─ Extract subject          │   │     ├─ Extract date & timing    │
    │    ├─ Parse timing (12-2pm)    │   │     ├─ Handle typos (tuseday)   │
    │    ├─ Parse date (tuesday)     │   │     └─ Validate teacher ID      │
    │    └─ Map subject (flask→py)   │   └─────────────────────────────────┘
    └─────────────────────────────────┘               │
                        │                               ▼
                        ▼                   ┌─────────────────────────────────┐
    ┌─────────────────────────────────┐   │   2. set_teacher_availability   │
    │   2. check_existing_session     │   │     ├─ Check existing records   │
    │     ├─ Query by subject & date  │   │     ├─ Insert/Update database  │
    │     ├─ Return session details   │   │     └─ Return confirmation     │
    │     └─ Check student count      │   └─────────────────────────────────┘
    └─────────────────────────────────┘               │
                        │                               ▼
            ┌───────────┼───────────┐         ┌─────────────────┐
            ▼                       ▼         │   RESPONSE      │
┌─────────────────────┐   ┌─────────────────────┐   │ "✅ Availability │
│   SESSION EXISTS    │   │  NO SESSION EXISTS  │   │ set for Tuesday  │
└─────────────────────┘   └─────────────────────┘   │ 12:00-17:00"    │
            │                       │         └─────────────────┘
            ▼                       ▼
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│  3. analyze_timing_conflict     │ │     4. create_new_session       │
│    ├─ Get existing students     │ │       ├─ Store student timing   │
│    ├─ AI conflict analysis      │ │       ├─ Create session record  │
│    ├─ Calculate optimal time    │ │       ├─ Enroll student         │
│    └─ Return recommendation     │ │       └─ Return confirmation    │
└─────────────────────────────────┘ └─────────────────────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────────────┐ ┌─────────────────┐
│   5. update_existing_session    │ │   RESPONSE      │
│     ├─ Add new student          │ │ "✅ Python session│
│     ├─ Update timing if needed  │ │ created for     │
│     ├─ Check teacher availability│ │ Tuesday 2-3 PM" │
│     └─ Optimize for all students│ └─────────────────┘
└─────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────┐
│  6. check_teacher_availability  │
│    ├─ Query teacher schedule    │
│    ├─ Validate time overlap     │
│    └─ Return availability status│
└─────────────────────────────────┘
            │
            ▼
    ┌─────────────────┐
    │   FINAL RESPONSE│
    │ "✅ Enrolled in │
    │ Python session  │
    │ Tuesday 2-3 PM  │
    │ (2 students)"   │
    └─────────────────┘
```

## 🛠️ AI Agent Tools Inventory

### 📊 **Data Retrieval Tools**
```
🔧 get_current_date()
   └─ Returns today's date for scheduling calculations

🔧 get_all_sessions_data()
   └─ Retrieves all active sessions and enrollment data
   └─ Used for system overview and debugging

🔧 get_all_data()
   └─ Comprehensive data dump for analysis
```

### 👨‍🎓 **Student Management Tools**
```
🔧 parse_student_request(input: JSON)
   ├─ Input: {"student_id": "xxx", "message": "I want Python 2-3 PM Tuesday"}
   ├─ Extracts: subject, timing, date, student_id
   ├─ Validates: timing patterns, subject keywords
   ├─ Maps: flask→python, react→react, spring→java
   └─ Output: Structured student request data

🔧 check_existing_session(input: JSON)
   ├─ Input: {"subject": "python", "date": "2025-08-19"}
   ├─ Queries: Database for matching sessions
   └─ Output: Session details or "not found"

🔧 create_new_session(input: JSON)
   ├─ Input: student_id, subject, date, start_time, end_time
   ├─ Creates: New session record
   ├─ Enrolls: Student automatically
   └─ Output: Success confirmation with session details

🔧 update_existing_session(input: JSON)
   ├─ Input: session_id, new_student_id, timing_preferences
   ├─ Adds: Student to existing session
   ├─ Optimizes: Timing for all enrolled students
   └─ Output: Updated session confirmation
```

### 👨‍🏫 **Teacher Management Tools**
```
🔧 parse_teacher_availability(input: JSON)
   ├─ Input: {"teacher_id": "xxx", "message": "Available Monday 12-5 PM"}
   ├─ Extracts: date, start_time, end_time, teacher_id
   ├─ Handles: Day names with typos (tuseday→tuesday)
   ├─ Calculates: Next occurrence of specified day
   └─ Output: Structured availability data

🔧 set_teacher_availability(input: JSON)
   ├─ Input: teacher_id, date, start_time, end_time
   ├─ Validates: Teacher authorization
   ├─ Updates: Database with availability
   └─ Output: Confirmation message

🔧 check_teacher_availability(input: JSON)
   ├─ Input: date, start_time, end_time
   ├─ Queries: Teacher schedule database
   ├─ Validates: Time overlap with proposed session
   └─ Output: Available/Not available status
```

### 🤖 **AI Analysis Tools**
```
🔧 analyze_timing_conflict(input: JSON)
   ├─ Input: Multiple student timing preferences
   ├─ AI Processing: Claude analyzes conflicts and overlaps
   ├─ Calculates: Optimal session timing
   ├─ Considers: Minimum 30-minute overlap requirement
   └─ Output: AI recommendation with reasoning

🔧 analyze_optimal_session_time(input: JSON)
   ├─ Input: Student availability data
   ├─ AI Processing: Advanced timing optimization
   ├─ Factors: Student preferences, teacher availability
   └─ Output: Optimized session schedule
```

### 🔄 **Utility & Helper Tools**
```
🔧 extract_subject_and_timing(message: str)
   ├─ Parses: Natural language for subjects and times
   ├─ Maps: Specific frameworks to broad categories
   └─ Returns: (subject, start_time, end_time)

🔧 calculate_optimal_timing(student_timings: list)
   ├─ Algorithmic: Backup for AI analysis
   ├─ Finds: Maximum overlap between student preferences
   └─ Returns: Optimal start and end times

🔧 normalize_subject(subject: str)
   ├─ Maps: All technology variants to main categories
   ├─ Examples: flask→python, nextjs→react, spring→java
   └─ Ensures: Consistent subject categorization

🔧 parse_time_from_message(message: str)
   ├─ Regex: Extracts time patterns (12-2pm, 1:30-2:30)
   ├─ Handles: Various time formats and AM/PM
   └─ Returns: Standardized 24-hour format

🔧 convert_time_format(time_str: str)
   └─ Utility: Time format conversions

🔧 time_to_minutes(time_str: str)
   └─ Converts: Time strings to minutes for calculations
```

## 🔄 **Tool Execution Flow Examples**

### Student Session Request Flow:
```
1. parse_student_request() → Extract "Python, 2-3 PM, Tuesday"
2. check_existing_session() → Find existing Python session
3. analyze_timing_conflict() → AI analyzes student timings
4. update_existing_session() → Add student with optimal timing
5. check_teacher_availability() → Verify teacher can teach
```

### Teacher Availability Flow:
```
1. parse_teacher_availability() → Extract "Monday, 12-5 PM"
2. set_teacher_availability() → Store in database
```

### AI Decision Making:
```
- Uses Claude 3 Haiku for natural language understanding
- LangGraph orchestrates tool execution
- Real-time conflict resolution
- Intelligent timing optimization
```
