'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Student, Session, SessionEnrollment } from '@/types'
import { Calendar, Clock, Users, BookOpen } from 'lucide-react'

interface StudentDashboardProps {
  student: Student
}

export default function StudentDashboard({ student }: StudentDashboardProps) {
  const [enrolledSessions, setEnrolledSessions] = useState<Session[]>([])
  const [availableSessions, setAvailableSessions] = useState<Session[]>([])
  const [requestForm, setRequestForm] = useState({
    subject: '',
    date: '',
    start_time: '',
    end_time: ''
  })

  useEffect(() => {
    fetchEnrolledSessions()
    fetchAvailableSessions()
  }, [student.id])

  const fetchEnrolledSessions = async () => {
    const { data } = await supabase
      .from('session_enrollments')
      .select(`
        *,
        sessions (*)
      `)
      .eq('student_id', student.id)
    
    if (data) {
      const sessions = data.map(enrollment => enrollment.sessions).filter(Boolean)
      setEnrolledSessions(sessions)
    }
  }

  const fetchAvailableSessions = async () => {
    const { data } = await supabase
      .from('sessions')
      .select('*')
      .eq('status', 'active')
      .order('date', { ascending: true })
    
    if (data) setAvailableSessions(data)
  }

  const requestSession = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // This would typically call your backend API
    const response = await fetch('/api/request-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: student.id,
        ...requestForm
      })
    })

    if (response.ok) {
      setRequestForm({ subject: '', date: '', start_time: '', end_time: '' })
      fetchEnrolledSessions()
      fetchAvailableSessions()
    }
  }

  const joinSession = async (sessionId: string) => {
    const { error } = await supabase
      .from('session_enrollments')
      .insert([{
        session_id: sessionId,
        student_id: student.id
      }])

    if (!error) {
      fetchEnrolledSessions()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Student Dashboard - {student.name}
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Request Session Form */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <BookOpen className="mr-2" size={20} />
                Request Session
              </h2>
              <form onSubmit={requestSession} className="grid grid-cols-2 gap-4">
                <input
                  type="text"
                  placeholder="Subject (e.g., Python, JavaScript)"
                  value={requestForm.subject}
                  onChange={(e) => setRequestForm({...requestForm, subject: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="date"
                  value={requestForm.date}
                  onChange={(e) => setRequestForm({...requestForm, date: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="time"
                  value={requestForm.start_time}
                  onChange={(e) => setRequestForm({...requestForm, start_time: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="time"
                  value={requestForm.end_time}
                  onChange={(e) => setRequestForm({...requestForm, end_time: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <button
                  type="submit"
                  className="col-span-2 bg-green-600 text-white rounded-lg px-4 py-2 hover:bg-green-700"
                >
                  Request Session
                </button>
              </form>
            </div>

            {/* Available Sessions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Calendar className="mr-2" size={20} />
                Available Sessions
              </h2>
              <div className="grid gap-4">
                {availableSessions.map((session) => (
                  <div key={session.id} className="border rounded-lg p-4 flex justify-between items-center">
                    <div>
                      <h3 className="font-medium text-blue-600">{session.subject}</h3>
                      <div className="text-sm text-gray-600 mt-1">
                        <p>{session.date} • {session.start_time} - {session.end_time}</p>
                        <p>{session.total_students} students enrolled</p>
                      </div>
                    </div>
                    <button
                      onClick={() => joinSession(session.id)}
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                    >
                      Join
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar - My Sessions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Users className="mr-2" size={20} />
              My Sessions
            </h2>
            <div className="space-y-4">
              {enrolledSessions.map((session) => (
                <div key={session.id} className="border rounded-lg p-4">
                  <h3 className="font-medium text-green-600">{session.subject}</h3>
                  <div className="text-sm text-gray-600 mt-2 space-y-1">
                    <p className="flex items-center">
                      <Calendar size={14} className="mr-1" />
                      {session.date}
                    </p>
                    <p className="flex items-center">
                      <Clock size={14} className="mr-1" />
                      {session.start_time} - {session.end_time}
                    </p>
                    <p className="flex items-center">
                      <Users size={14} className="mr-1" />
                      {session.total_students} students
                    </p>
                  </div>
                  {session.meet_link && (
                    <a
                      href={session.meet_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-3 bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                    >
                      Join Meeting
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}