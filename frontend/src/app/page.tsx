'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import ChatInterface from '@/components/ChatInterface'
import { Users } from 'lucide-react'

export default function Home() {
  const [mounted, setMounted] = useState(false)

  // Fix hydration issues
  useEffect(() => {
    setMounted(true)
  }, [])

  // Prevent hydration mismatch
  if (!mounted) {
    return null
  }

  // Show portal selection page
  console.log('❌ No user found, showing portal selection')
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <Users size={64} className="text-blue-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Session Scheduler</h1>
          <p className="text-gray-600">Choose your portal</p>
        </div>

        <div className="space-y-4">
          <a
            href="/student"
            className="w-full flex items-center justify-center space-x-3 bg-blue-600 text-white rounded-lg px-6 py-4 hover:bg-blue-700 transition-colors block text-decoration-none"
          >
            <span className="text-lg">👨‍🎓</span>
            <div className="text-left">
              <div className="font-medium">Student Portal</div>
              <div className="text-sm text-blue-100">Book learning sessions</div>
            </div>
          </a>

          <a
            href="/teacher"
            className="w-full flex items-center justify-center space-x-3 bg-green-600 text-white rounded-lg px-6 py-4 hover:bg-green-700 transition-colors block text-decoration-none"
          >
            <span className="text-lg">👨‍🏫</span>
            <div className="text-left">
              <div className="font-medium">Teacher Portal</div>
              <div className="text-sm text-green-100">Set availability & teach</div>
            </div>
          </a>
        </div>

        <div className="text-center text-sm text-gray-500 mt-6">
          Select your role to continue
        </div>
      </div>
    </div>
  )
}