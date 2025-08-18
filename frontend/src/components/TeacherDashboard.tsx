'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Teacher, Session, TeacherAvailability } from '@/types'
import { Calendar, Clock, Users, Plus, Filter } from 'lucide-react'

interface TeacherDashboardProps {
  teacher: Teacher
}

export default function TeacherDashboard({ teacher }: TeacherDashboardProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [availability, setAvailability] = useState<TeacherAvailability[]>([])
  const [sessionFilter, setSessionFilter] = useState<string>('today_future')
  const [loading, setLoading] = useState(false)
  const [newAvailability, setNewAvailability] = useState({
    date: '',
    start_time: '',
    end_time: '',
    subject: ''
  })

  useEffect(() => {
    fetchSessions()
    fetchAvailability()
  }, [teacher.id, sessionFilter])

  const fetchSessions = async () => {
    setLoading(true)
    try {
      console.log('=== DEBUGGING SESSION FETCH ===')
      console.log('Teacher object:', teacher)
      console.log('Teacher ID:', teacher.id)
      console.log('Filter:', sessionFilter)
      
      // First, let's check if there are ANY sessions in the database
      const { data: allSessions, error: allError } = await supabase
        .from('sessions')
        .select('*')
      
      console.log('All sessions in database:', allSessions?.length || 0)
      console.log('All sessions data:', allSessions)
      
      if (allError) {
        console.error('Error fetching all sessions:', allError)
      }
      
      // Now fetch sessions for this specific teacher
      const { data, error } = await supabase
        .from('sessions')
        .select('*')
        .eq('teacher_id', teacher.id)
        .order('date', { ascending: true })
      
      console.log('Sessions for teacher:', data?.length || 0)
      console.log('Teacher sessions data:', data)
      
      if (error) {
        console.error('Supabase error:', error)
        setSessions([])
        return
      }

      if (!data || data.length === 0) {
        console.log('No sessions found for this teacher')
        setSessions([])
        return
      }

      console.log('Raw sessions from DB:', data.length)

      // Apply date filtering
      const today = new Date()
      today.setHours(0, 0, 0, 0) // Reset time to start of day
      
      let filteredSessions = data

      if (sessionFilter === 'today_future') {
        filteredSessions = data.filter(session => {
          const sessionDate = new Date(session.date)
          sessionDate.setHours(0, 0, 0, 0)
          return sessionDate >= today
        })
      } else if (sessionFilter === 'today') {
        filteredSessions = data.filter(session => {
          const sessionDate = new Date(session.date)
          sessionDate.setHours(0, 0, 0, 0)
          return sessionDate.getTime() === today.getTime()
        })
      } else if (sessionFilter === 'future') {
        filteredSessions = data.filter(session => {
          const sessionDate = new Date(session.date)
          sessionDate.setHours(0, 0, 0, 0)
          return sessionDate > today
        })
      }
      // 'all' filter shows everything, no filtering needed

      console.log('Filtered sessions:', filteredSessions.length)
      console.log('Final sessions to display:', filteredSessions)
      setSessions(filteredSessions)
      
    } catch (error) {
      console.error('Error fetching sessions:', error)
      setSessions([])
    } finally {
      setLoading(false)
    }
  }

  const fetchAvailability = async () => {
    const { data } = await supabase
      .from('teacher_availability')
      .select('*')
      .eq('teacher_id', teacher.id)
      .order('date', { ascending: true })
    
    if (data) setAvailability(data)
  }

  const addAvailability = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const { error } = await supabase
      .from('teacher_availability')
      .insert([{
        teacher_id: teacher.id,
        ...newAvailability
      }])

    if (!error) {
      setNewAvailability({ date: '', start_time: '', end_time: '', subject: '' })
      fetchAvailability()
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Teacher Dashboard - {teacher.name}
        </h1>

        {/* Debug Info */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-yellow-800 mb-2">Debug Info:</h3>
          <p className="text-sm text-yellow-700">Teacher ID: {teacher.id}</p>
          <p className="text-sm text-yellow-700">Filter: {sessionFilter}</p>
          <p className="text-sm text-yellow-700">Sessions Count: {sessions.length}</p>
          <p className="text-sm text-yellow-700">Loading: {loading ? 'Yes' : 'No'}</p>
        </div>

        {/* Session Statistics */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center">
              <Users className="h-8 w-8 text-blue-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Total Sessions</p>
                <p className="text-2xl font-semibold text-gray-900">{sessions.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center">
              <Calendar className="h-8 w-8 text-green-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Active Sessions</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {sessions.filter(s => s.status === 'active').length}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-orange-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Total Students</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {sessions.reduce((sum, s) => sum + (s.total_students || 0), 0)}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center">
              <Plus className="h-8 w-8 text-purple-500" />
              <div className="ml-3">
                <p className="text-sm font-medium text-gray-500">Availability Slots</p>
                <p className="text-2xl font-semibold text-gray-900">{availability.length}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Add Availability Form */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Plus className="mr-2" size={20} />
                Set Availability
              </h2>
              <form onSubmit={addAvailability} className="grid grid-cols-2 gap-4">
                <input
                  type="date"
                  value={newAvailability.date}
                  onChange={(e) => setNewAvailability({...newAvailability, date: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="text"
                  placeholder="Subject (e.g., Python, JavaScript)"
                  value={newAvailability.subject}
                  onChange={(e) => setNewAvailability({...newAvailability, subject: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="time"
                  value={newAvailability.start_time}
                  onChange={(e) => setNewAvailability({...newAvailability, start_time: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <input
                  type="time"
                  value={newAvailability.end_time}
                  onChange={(e) => setNewAvailability({...newAvailability, end_time: e.target.value})}
                  className="border rounded-lg px-3 py-2"
                  required
                />
                <button
                  type="submit"
                  className="col-span-2 bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700"
                >
                  Add Availability
                </button>
              </form>
            </div>

            {/* Current Availability */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <Calendar className="mr-2" size={20} />
                Your Availability
              </h2>
              <div className="space-y-3">
                {availability.map((slot) => (
                  <div key={slot.id} className="border rounded-lg p-4 flex justify-between items-center">
                    <div>
                      <p className="font-medium">{slot.subject}</p>
                      <p className="text-sm text-gray-600">
                        {slot.date} • {slot.start_time} - {slot.end_time}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar - Scheduled Sessions */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold flex items-center">
                <Users className="mr-2" size={20} />
                Your Sessions
              </h2>
              <div className="flex items-center space-x-2">
                <Filter size={16} className="text-gray-500" />
                <select
                  value={sessionFilter}
                  onChange={(e) => setSessionFilter(e.target.value)}
                  className="text-sm border rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Sessions</option>
                  <option value="today_future">Today & Future</option>
                  <option value="today">Today Only</option>
                  <option value="future">Future Only</option>
                </select>
              </div>
            </div>
            
            {loading ? (
              <div className="text-center py-4 text-gray-500">Loading sessions...</div>
            ) : (
              <div className="space-y-4 max-h-96 overflow-y-auto">
                {sessions.length === 0 ? (
                  <div className="text-center py-4 text-gray-500">
                    No sessions found for the selected filter.
                  </div>
                ) : (
                  sessions.map((session) => {
                    const sessionDate = new Date(session.date)
                    const today = new Date()
                    const isPast = sessionDate < today
                    const isToday = sessionDate.toDateString() === today.toDateString()
                    
                    return (
                      <div 
                        key={session.id} 
                        className={`border rounded-lg p-4 hover:shadow-md transition-shadow ${
                          isPast ? 'bg-gray-50 border-gray-200' : 'bg-white border-gray-300'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <h3 className={`font-medium ${isPast ? 'text-gray-500' : 'text-blue-600'}`}>
                            {session.subject}
                          </h3>
                          {isToday && (
                            <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">
                              Today
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600 mt-2 space-y-1">
                          <p className="flex items-center">
                            <Calendar size={14} className="mr-1" />
                            {sessionDate.toLocaleDateString()}
                          </p>
                          <p className="flex items-center">
                            <Clock size={14} className="mr-1" />
                            {session.start_time} - {session.end_time}
                          </p>
                          <p className="flex items-center">
                            <Users size={14} className="mr-1" />
                            {session.total_students || 0} students enrolled
                          </p>
                          {session.meet_link && !isPast && (
                            <p className="text-xs">
                              <a 
                                href={session.meet_link} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline"
                              >
                                Join Meeting
                              </a>
                            </p>
                          )}
                        </div>
                        <div className="mt-3 flex items-center justify-between">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            session.status === 'active' 
                              ? 'bg-green-100 text-green-800' 
                              : session.status === 'completed'
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}>
                            {session.status}
                          </span>
                          <span className="text-xs text-gray-400">
                            ID: {session.id.slice(0, 8)}...
                          </span>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}