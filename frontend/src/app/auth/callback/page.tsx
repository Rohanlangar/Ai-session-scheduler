'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function AuthCallback() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState('Processing...')

  const autoAssignRole = async (user: any) => {
    try {
      setStatus('Setting up your account...')
      
      // Check if user already has a role
      const { data: teacherData } = await supabase
        .from('teachers')
        .select('id')
        .eq('id', user.id)
        .maybeSingle()

      const { data: studentData } = await supabase
        .from('students')
        .select('user_id')
        .eq('user_id', user.id)
        .maybeSingle()

      // If user already has a role, don't create another one
      if (teacherData || studentData) {
        console.log('✅ User already has role assigned')
        return
      }

      const userData = {
        id: user.id,
        user_id: user.id,
        name: user.user_metadata?.name || 
              user.user_metadata?.full_name || 
              user.email?.split('@')[0] || 
              'User',
        email: user.email || ''
      }
      
      // Check if this is the specific teacher ID
      const TEACHER_ID = 'e4bcab2f-8da5-4a78-85e8-094f4d7ac308'
      
      if (user.id === TEACHER_ID) {
        // Create teacher account
        await supabase.from('teachers').insert({
          id: userData.id,
          name: userData.name,
          email: userData.email
        })
        console.log('✅ Teacher account created for:', user.email)
      } else {
        // Create student account for everyone else
        await supabase.from('students').insert({
          user_id: userData.user_id,
          name: userData.name,
          email: userData.email
        })
        console.log('✅ Student account created for:', user.email)
      }
      
    } catch (error: any) {
      console.error('Error auto-assigning role:', error)
      // Don't throw error, just log it
    }
  }

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        setStatus('Authenticating...')
        
        // Check for error in URL params
        const error = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')
        
        if (error) {
          console.error('OAuth error:', error, errorDescription)
          setStatus('Authentication failed')
          setTimeout(() => router.push('/auth?error=oauth_error'), 2000)
          return
        }

        // Wait a moment for Supabase to process the OAuth callback
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        // Get the current session
        const { data, error: sessionError } = await supabase.auth.getSession()
        
        if (sessionError) {
          console.error('Session error:', sessionError)
          setStatus('Session error')
          setTimeout(() => router.push('/auth?error=session_error'), 2000)
          return
        }

        if (data.session?.user) {
          console.log('✅ User authenticated:', data.session.user.email)
          setStatus('Welcome! Setting up your account...')
          
          // Auto-assign role based on user ID
          await autoAssignRole(data.session.user)
          
          setStatus('Redirecting to dashboard...')
          setTimeout(() => router.push('/dashboard'), 1000)
        } else {
          console.log('❌ No session found')
          setStatus('No session found')
          setTimeout(() => router.push('/auth'), 2000)
        }
      } catch (error) {
        console.error('Callback handling error:', error)
        setStatus('Something went wrong')
        setTimeout(() => router.push('/auth?error=callback_error'), 2000)
      }
    }

    handleAuthCallback()
  }, [router, searchParams])

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-gray-900 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">{status}</p>
      </div>
    </div>
  )
}