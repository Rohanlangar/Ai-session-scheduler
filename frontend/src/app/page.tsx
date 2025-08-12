'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import ChatInterface from '@/components/ChatInterface'
import { Users } from 'lucide-react'

export default function Home() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Prevent infinite loading
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (loading) {
        console.log('⏰ Loading timeout - forcing stop')
        setLoading(false)
      }
    }, 5000)

    return () => clearTimeout(timeout)
  }, [loading])
  const [isStudent, setIsStudent] = useState<boolean | null>(null)

  const checkIfStudent = async (userId: string): Promise<boolean> => {
    try {
      const { data } = await supabase
        .from('students')
        .select('user_id')
        .eq('user_id', userId)
      
      return data && data.length > 0
    } catch (error) {
      console.error('Error checking student:', error)
      return false
    }
  }

  const createStudentAccount = async (user: User) => {
    try {
      const userData = {
        user_id: user.id,
        name: user.user_metadata?.name || 
              user.user_metadata?.full_name || 
              user.email?.split('@')[0] || 
              'Student',
        email: user.email
      }
      
      await supabase.from('students').insert(userData)
      console.log('✅ Student account created')
      return true
    } catch (error) {
      console.error('❌ Error creating student account:', error)
      return false
    }
  }

  const handleGoogleSignIn = async () => {
    setLoading(true)
    try {
      // Clear any existing session first
      await supabase.auth.signOut()
      
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          }
        }
      })
      if (error) throw error
    } catch (error) {
      console.error('Google auth error:', error)
      alert('Error signing in. Please try again.')
      setLoading(false)
    }
  }

  useEffect(() => {
    const initAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        
        if (session?.user) {
          setUser(session.user)
          const studentExists = await checkIfStudent(session.user.id)
          
          if (!studentExists) {
            await createStudentAccount(session.user)
          }
          
          setIsStudent(true)
        }
      } catch (error) {
        console.error('Auth error:', error)
      } finally {
        setLoading(false)
      }
    }

    initAuth()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session?.user) {
        setUser(session.user)
        const studentExists = await checkIfStudent(session.user.id)
        
        if (!studentExists) {
          await createStudentAccount(session.user)
        }
        
        setIsStudent(true)
      } else {
        setUser(null)
        setIsStudent(null)
      }
      setLoading(false)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Show chat if user is logged in
  if (user && isStudent) {
    return <ChatInterface user={user} isTeacher={false} />
  }

  // Show login page
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <Users size={64} className="text-green-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Session Scheduler</h1>
          <p className="text-gray-600">Student Portal</p>
        </div>

        <button
          onClick={handleGoogleSignIn}
          disabled={loading}
          className="w-full flex items-center justify-center space-x-3 bg-white border border-gray-300 rounded-lg px-6 py-3 hover:bg-gray-50 transition-colors mb-4"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          <span className="text-gray-700">Sign in with Google</span>
        </button>

        <div className="text-center text-sm text-gray-500">
          Sign in to schedule your AI learning sessions
        </div>
      </div>
    </div>
  )
}