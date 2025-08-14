'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { Send, Bot, User, Calendar, Clock, Users, ArrowRight, Sparkles, Zap } from 'lucide-react'
import { User as SupabaseUser } from '@supabase/supabase-js'

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
}

interface Session {
  id: string
  subject: string
  date: string
  start_time: string
  end_time: string
  meet_link?: string
  status: string
  total_students: number
}



interface ChatInterfaceProps {
  user: SupabaseUser
  isTeacher: boolean
}

export default function ChatInterface({ user, isTeacher }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: isTeacher
        ? "Hi! I'm your AI scheduling assistant. You can tell me your availability like 'I'm available Monday 2-4 PM for Python sessions' and I'll help manage your schedule."
        : "Hi! I'm your AI scheduling assistant. Tell me when you're available for sessions like 'I'm free Monday 2-4 PM for Python' and I'll find or create the perfect session for you.",
      isUser: false,
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessions, setSessions] = useState<Session[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const fetchSessions = useCallback(async () => {
    try {
      console.log('🔄 Fetching sessions for user:', user.id, 'isTeacher:', isTeacher)

      // Get current date for filtering today and above
      const today = new Date().toISOString().split('T')[0]
      console.log('📅 Filtering sessions from date:', today)

      if (isTeacher) {
        const { data, error } = await supabase
          .from('sessions')
          .select('*')
          .eq('teacher_id', user.id)
          .gte('date', today) // Today and above
          .eq('status', 'active')
          .order('date', { ascending: true })

        console.log('Teacher sessions (today and above):', data, error)
        if (data) setSessions(data)
      } else {
        // For students, get sessions they're enrolled in (today and above)
        const { data, error } = await supabase
          .from('session_enrollments')
          .select(`
            session_id,
            sessions!inner (
              id,
              subject,
              date,
              start_time,
              end_time,
              meet_link,
              status,
              total_students
            )
          `)
          .eq('student_id', user.id)
          .gte('sessions.date', today) // Today and above
          .eq('sessions.status', 'active')

        console.log('Student enrollments (today and above):', data, error)

        if (data && data.length > 0) {
          const userSessions = (data as any[])
            .map((enrollment: any) => enrollment.sessions)
            .filter(Boolean)
            .filter((session: Session) => session.date >= today) // Double check for today and above
          console.log('Mapped sessions (today and above):', userSessions)
          setSessions(userSessions)
        } else {
          // No enrollments found - show empty
          console.log('No enrollments found for this student from today onwards')
          setSessions([])
        }
      }
    } catch (error) {
      console.error('Error fetching sessions:', error)
      setSessions([])
    }
  }, [user.id, isTeacher])

  useEffect(() => {
    fetchSessions()
    scrollToBottom()
  }, [messages, fetchSessions])

  // Real-time session updates using Supabase subscriptions
  useEffect(() => {
    console.log('🔄 Setting up real-time session updates...')

    // Subscribe to session changes
    const sessionSubscription = supabase
      .channel('sessions')
      .on('postgres_changes',
        { event: '*', schema: 'public', table: 'sessions' },
        (payload) => {
          console.log('📡 Session updated:', payload)
          fetchSessions() // Refresh when sessions change
        }
      )
      .on('postgres_changes',
        { event: '*', schema: 'public', table: 'session_enrollments' },
        (payload) => {
          console.log('📡 Enrollment updated:', payload)
          fetchSessions() // Refresh when enrollments change
        }
      )
      .subscribe()

    // Fallback: Auto-refresh every 2 seconds for instant updates
    const interval = setInterval(() => {
      console.log('🔄 Auto-refreshing sessions...')
      fetchSessions()
    }, 2000)

    return () => {
      console.log('🔄 Cleaning up subscriptions...')
      sessionSubscription.unsubscribe()
      clearInterval(interval)
    }
  }, [fetchSessions])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }



  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      isUser: true,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsLoading(true)

    try {
      // Call your backend API
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      console.log('🔄 Sending request to:', `${backendUrl}/api/chat-session`)

      const response = await fetch(`${backendUrl}/api/chat-session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          user_id: user.id,
          is_teacher: isTeacher
        })
      })

      console.log('📡 Response status:', response.status)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('📝 Response data:', data)

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response || 'I understand! Let me process that for you.',
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, botMessage])

      // INSTANT session refresh - multiple attempts for reliability
      fetchSessions()

      setTimeout(() => fetchSessions(), 100)
      setTimeout(() => fetchSessions(), 300)
      setTimeout(() => fetchSessions(), 600)
      setTimeout(() => fetchSessions(), 1000)

    } catch (error) {
      console.error('❌ Frontend request error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `Connection error: ${error instanceof Error ? error.message : 'Please check if backend is running on port 8080'}`,
        isUser: false,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }



  return (
    <div className="h-screen bg-white flex">
      {/* Chat Area - 70% */}
      <div className="flex-1 flex flex-col" style={{ width: '70%' }}>
        {/* Header */}
        <div className="bg-white px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
                {isTeacher ? <Zap className="w-5 h-5 text-white" /> : <Sparkles className="w-5 h-5 text-white" />}
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">
                  {isTeacher ? 'Teacher Studio' : 'Learning Hub'}
                </h1>
                <p className="text-gray-600 text-sm">
                  Welcome back, {user.user_metadata?.name || user.email?.split('@')[0] || 'User'}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
                <span className="text-white font-medium text-sm">
                  {user.user_metadata?.name?.charAt(0) || user.email?.charAt(0) || 'U'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-3 rounded-xl shadow-sm border transition-all duration-200 ${message.isUser
                  ? 'bg-gray-900 text-white border-gray-800'
                  : 'bg-white text-gray-900 border-gray-200'
                  }`}
              >
                <div className="flex items-start space-x-3">
                  {!message.isUser && (
                    <div className="w-7 h-7 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot size={14} className="text-white" />
                    </div>
                  )}
                  {message.isUser && (
                    <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                      <User size={14} className="text-white" />
                    </div>
                  )}
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <p className={`text-xs mt-2 ${message.isUser ? 'text-gray-300' : 'text-gray-500'
                      }`}>
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white text-gray-900 border border-gray-200 px-4 py-3 rounded-xl shadow-sm">
                <div className="flex items-center space-x-3">
                  <div className="w-7 h-7 bg-gray-900 rounded-lg flex items-center justify-center">
                    <Bot size={14} className="text-white" />
                  </div>
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="bg-white border-t border-gray-200 p-6">
          <div className="flex space-x-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder={isTeacher
                ? "Set your availability! e.g., 'I'm available Friday 12-5 PM'"
                : "Ask me anything! e.g., 'I want Python session 2-3 PM'"
              }
              className="flex-1 border border-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent text-gray-900 placeholder-gray-500 transition-all duration-200"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="bg-gray-900 text-white px-6 py-3 rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-all duration-200"
            >
              <Send size={18} />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>

      {/* Sessions Sidebar - 30% */}
      <div className="bg-gray-50 border-l border-gray-200" style={{ width: '30%' }}>
        <div className="p-6 border-b border-gray-200 bg-white">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-gray-900 flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-gray-900" />
                <span>Sessions</span>
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Today & upcoming
              </p>
            </div>
            <button
              onClick={fetchSessions}
              className="text-gray-600 hover:text-gray-900 text-sm font-medium px-3 py-1 rounded-lg hover:bg-gray-100 transition-all duration-200"
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="p-4 space-y-3 overflow-y-auto" style={{ height: 'calc(100vh - 140px)' }}>
          {sessions.length === 0 ? (
            <div className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Calendar className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-gray-500 font-medium">No sessions found</p>
              <p className="text-sm text-gray-400 mt-1">Sessions from today onwards will appear here</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div key={session.id} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow duration-200">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-bold text-lg text-gray-900 capitalize flex items-center space-x-2">
                    <div className="w-3 h-3 bg-gray-900 rounded-full"></div>
                    <span>{session.subject}</span>
                  </h3>
                  <span className={`px-2 py-1 rounded-lg text-xs font-medium ${session.status === 'active'
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-gray-100 text-gray-700 border border-gray-200'
                    }`}>
                    {session.status}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Calendar className="w-4 h-4 text-gray-500" />
                    <span>{session.date}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span>{session.start_time?.slice(0, 5)} - {session.end_time?.slice(0, 5)}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <Users className="w-4 h-4 text-gray-500" />
                    <span>{session.total_students} students</span>
                  </div>
                </div>

                {session.meet_link && (
                  <a
                    href={session.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full bg-gray-900 text-white py-2 px-4 rounded-lg hover:bg-gray-800 transition-all duration-200 flex items-center justify-center space-x-2 text-sm font-medium"
                  >
                    <span>Join Meeting</span>
                    <ArrowRight className="w-4 h-4" />
                  </a>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>

  )
}