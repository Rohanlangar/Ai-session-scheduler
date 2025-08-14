'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function AuthCallback() {
  const router = useRouter()

  const autoAssignRole = async (user: any) => {
    try {
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
    }
  }

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Handle OAuth callback
        const hashParams = new URLSearchParams(window.location.hash.substring(1))
        const searchParams = new URLSearchParams(window.location.search)
        
        // Check for OAuth code or hash parameters
        const code = searchParams.get('code')
        const accessToken = hashParams.get('access_token')
        
        if (code || accessToken) {
          // Let Supabase handle the OAuth callback
          const { data, error } = await supabase.auth.getSession()
          
          if (error) {
            console.error('Auth callback error:', error)
            router.push('/auth?error=callback_error')
            return
          }

          if (data.session?.user) {
            // Auto-assign role based on user ID
            await autoAssignRole(data.session.user)
            router.push('/dashboard')
          } else {
            router.push('/auth')
          }
        } else {
          // No OAuth parameters, redirect to auth
          router.push('/auth')
        }
      } catch (error) {
        console.error('Callback handling error:', error)
        router.push('/auth?error=callback_error')
      }
    }

    handleAuthCallback()
  }, [router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-600">Completing sign in...</p>
      </div>
    </div>
  )
}