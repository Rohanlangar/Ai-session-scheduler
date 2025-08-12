'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Teacher, Session, TeacherAvailability } from '@/types'
import { Calendar, Clock, Users, Plus } from 'lucide-react'

interface TeacherDashboardProps {
  teacher: Teacher
}

export default function TeacherDashboard({ teacher }: TeacherDashboardProps) {
  const [sessions, setSessions] = useState<Session[]>([])
  const [availability, setAvailability] = useState<TeacherAvailability[]>([])
  const [newAvailability, setNewAvailability] = useState({
    date: '',
    start_time: '',
    end_time: '',
    subject: ''
  })

  useEffect(() => {
    fetchSessions()
    fetchAvailability()
  }, [teacher.id])

  const fetchSessions = async () => {
    const { data } = await supabase
      .from('sessions')
      .select('*')
      .eq('teacher_id', teacher.id)
      .order('date', { ascending: true })
    
    if (data) setSessions(data)
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
            <h2 className="text-xl font-semibold mb-4 flex items-center">
              <Users className="mr-2" size={20} />
              Scheduled Sessions
            </h2>
            <div className="space-y-4">
              {sessions.map((session) => (
                <div key={session.id} className="border rounded-lg p-4">
                  <h3 className="font-medium text-blue-600">{session.subject}</h3>
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
                  <div className="mt-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      session.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {session.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}