'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import ChatInterface from '@/components/ChatInterface'
import { GraduationCap, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function StudentPortal() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authReady, setAuthReady] = useState(false)
  const [mounted, setMounted] = useState(false)

  // Fix hydration issues
  useEffect(() => {
    setMounted(true)
  }, [])

  const handleGoogleSignIn = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        }
      })
      if (error) throw error
    } catch (error) {
      console.error('Google auth error:', error)
      alert('Error signing in. Please try again.')
    }
  }

  const createStudentAccount = async (user: User) => {
    try {
      console.log('🔄 Creating student account for:', user.email)
      
      // Check if student already exists
      const { data: existingStudent, error: selectError } = await supabase
        .from('students')
        .select('user_id')
        .eq('user_id', user.id)
        .maybeSingle()
      
      if (selectError) {
        console.error('Error checking student:', selectError)
        return
      }
      
      if (!existingStudent) {
        // Create student account
        const userData = {
          user_id: user.id,
          name: user.user_metadata?.name || 
                user.user_metadata?.full_name || 
                user.email?.split('@')[0] || 
                'Student',
          email: user.email || ''
        }
        
        const { data, error } = await supabase.from('students').insert(userData).select()
        if (error) {
          console.error('❌ Error creating student:', error)
        } else {
          console.log('✅ Student account created:', data)
        }
      } else {
        console.log('✅ Student already exists')
      }
    } catch (error) {
      console.error('❌ Error in createStudentAccount:', error)
    }
  }

  useEffect(() => {
    let mounted = true
    let timeoutId: NodeJS.Timeout

    const initializeAuth = async () => {
      try {
        console.log('🔄 Initializing student authentication...')
        
        timeoutId = setTimeout(() => {
          if (mounted && loading) {
            console.log('⏰ Auth timeout - stopping loading')
            setAuthReady(true)
            setLoading(false)
          }
        }, 3000)
        
        // Get initial session
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('Session error:', error)
        } else if (session?.user && mounted) {
          console.log('✅ Found existing session for student:', session.user.email)
          setUser(session.user)
          await createStudentAccount(session.user)
        }
        
        if (mounted) {
          clearTimeout(timeoutId)
          setAuthReady(true)
          setLoading(false)
        }
      } catch (error) {
        console.error('Auth initialization error:', error)
        if (mounted) {
          clearTimeout(timeoutId)
          setAuthReady(true)
          setLoading(false)
        }
      }
    }

    initializeAuth()

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('🔄 Student auth state change:', event, session?.user?.email || 'no user')
      
      if (!mounted) return

      if (event === 'SIGNED_IN' && session?.user) {
        console.log('✅ Student signed in:', session.user.email)
        setUser(session.user)
        await createStudentAccount(session.user)
        setAuthReady(true)
        setLoading(false)
      } else if (event === 'SIGNED_OUT') {
        console.log('❌ Student signed out')
        setUser(null)
        setAuthReady(true)
        setLoading(false)
      } else if (event === 'TOKEN_REFRESHED') {
        console.log('🔄 Token refreshed')
        if (session?.user) {
          setUser(session.user)
        }
      }
    })

    return () => {
      mounted = false
      if (timeoutId) clearTimeout(timeoutId)
      subscription.unsubscribe()
    }
  }, [])

  // Prevent hydration mismatch
  if (!mounted) {
    return null
  }

  // Show loading spinner
  if (loading || !authReady) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Show chat interface if user is authenticated
  if (user) {
    console.log('✅ Rendering student chat interface for:', user.email)
    return <ChatInterface user={user} isTeacher={false} />
  }

  // Show student login page
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
        <div className="flex items-center mb-6">
          <Link href="/" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </Link>
          <span className="ml-2 text-gray-500">Back to portal selection</span>
        </div>

        <div className="text-center mb-8">
          <GraduationCap size={64} className="text-blue-600 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Student Portal</h1>
          <p className="text-gray-600">Book AI learning sessions</p>
        </div>

        <button
          onClick={handleGoogleSignIn}
          className="w-full flex items-center justify-center space-x-3 bg-white border border-gray-300 rounded-lg px-6 py-3 hover:bg-gray-50 transition-colors mb-4"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12 1 13.78 1.43 15.45 2.18 16.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          <span className="text-gray-700">Sign in with Google</span>
        </button>

        <div className="text-center text-sm text-gray-500">
          Sign in to book your AI learning sessions
        </div>
      </div>
    </div>
  )
}