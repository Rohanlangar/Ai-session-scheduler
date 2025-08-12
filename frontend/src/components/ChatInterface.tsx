'use client'

import { useState, useEffect, useRef } from 'react'
import { supabase } from '@/lib/supabase'
import { Send, Bot, User, LogOut } from 'lucide-react'
import { User as SupabaseUser } from '@supabase/supabase-js'

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
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
  const [sessions, setSessions] = useState<any[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchSessions()
    scrollToBottom()
  }, [messages])

  // Auto-refresh sessions every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSessions()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchSessions = async () => {
    try {
      console.log('🔄 Fetching sessions for user:', user.id, 'isTeacher:', isTeacher)
      
      if (isTeacher) {
        const { data, error } = await supabase
          .from('sessions')
          .select('*')
          .eq('teacher_id', user.id)
          .order('date', { ascending: true })
        
        console.log('Teacher sessions:', data, error)
        if (data) setSessions(data)
      } else {
        // For students, get sessions they're enrolled in
        const { data, error } = await supabase
          .from('session_enrollments')
          .select(`
            session_id,
            sessions (
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
        
        console.log('Student enrollments:', data, error)
        
        if (data && data.length > 0) {
          const userSessions = data.map(enrollment => enrollment.sessions).filter(Boolean)
          console.log('Mapped sessions:', userSessions)
          setSessions(userSessions)
        } else {
          // No enrollments found - show empty
          console.log('No enrollments found for this student')
          setSessions([])
        }
      }
    } catch (error) {
      console.error('Error fetching sessions:', error)
      setSessions([])
    }
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
      const response = await fetch('http://localhost:8001/api/chat-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: inputMessage,
          user_id: user.id,
          is_teacher: isTeacher
        })
      })

      const data = await response.json()
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.response || 'I understand! Let me process that for you.',
        isUser: false,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, botMessage])
      
      // Refresh sessions immediately after AI response
      setTimeout(() => {
        fetchSessions()
      }, 1000) // Small delay to ensure backend has processed
      
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
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

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut()
      // Force page reload to clear all state
      window.location.href = '/'
    } catch (error) {
      console.error('Logout error:', error)
      // Force reload anyway
      window.location.href = '/'
    }
  }

  return (
    <div className="h-screen bg-gray-50 flex">
      {/* Chat Area - 70% */}
      <div className="flex-1 flex flex-col" style={{ width: '70%' }}>
        {/* Header */}
        <div className="bg-white border-b px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              AI Session Scheduler
            </h1>
            <p className="text-sm text-gray-600">
              {isTeacher ? 'Teacher' : 'Student'} - {user.user_metadata?.name || user.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-800"
          >
            <LogOut size={20} />
            <span>Logout</span>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.isUser
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-900 border'
                }`}
              >
                <div className="flex items-start space-x-2">
                  {!message.isUser && <Bot size={16} className="mt-1 text-blue-600" />}
                  {message.isUser && <User size={16} className="mt-1" />}
                  <div className="flex-1">
                    <p className="text-sm">{message.content}</p>
                    <p className={`text-xs mt-1 ${
                      message.isUser ? 'text-blue-100' : 'text-gray-500'
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
              <div className="bg-white text-gray-900 border px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Bot size={16} className="text-blue-600" />
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
        <div className="bg-white border-t p-4">
          <div className="flex space-x-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isTeacher 
                ? "Tell me your availability (e.g., 'I'm available Monday 2-4 PM for Python')"
                : "When are you available? (e.g., 'I'm free Monday 2-4 PM for Python')"
              }
              className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 bg-white"
              disabled={isLoading}
              style={{ color: '#000000' }}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <Send size={20} />
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>

      {/* Sessions Sidebar - 30% */}
      <div className="bg-white border-l" style={{ width: '30%' }}>
        <div className="p-4 border-b flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">
            {isTeacher ? 'My Sessions' : 'Enrolled Sessions'}
          </h2>
          <button
            onClick={fetchSessions}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Refresh
          </button>
        </div>
        <div className="p-4 space-y-4 overflow-y-auto" style={{ height: 'calc(100vh - 80px)' }}>
          {sessions.length === 0 ? (
            <p className="text-gray-500 text-center">No sessions yet</p>
          ) : (
            sessions.map((session) => (
              <div key={session.id} className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-medium text-blue-600">{session.subject}</h3>
                <div className="text-sm text-gray-600 mt-2 space-y-1">
                  <p>📅 {session.date}</p>
                  <p>🕐 {session.start_time} - {session.end_time}</p>
                  <p>👥 {session.total_students} students</p>
                </div>
                <div className="mt-3">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    session.status === 'active' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {session.status}
                  </span>
                </div>
                {session.meet_link && (
                  <a
                    href={session.meet_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-2 bg-blue-600 text-white px-3 py-1 rounded text-xs hover:bg-blue-700"
                  >
                    Join Meeting
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