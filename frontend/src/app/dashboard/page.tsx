'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { useRouter } from 'next/navigation'
import Navbar from '@/components/Navbar'
import ChatInterface from '@/components/ChatInterface'

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null)
  const [isTeacher, setIsTeacher] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [mounted, setMounted] = useState(false)
  const router = useRouter()

  const autoAssignRole = async (user: User) => {
    try {
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
    setMounted(true)
  }, [])

  useEffect(() => {
    const checkUserAndRole = async () => {
      try {
        // Get current session
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('Session error:', error)
          router.push('/auth')
          return
        }

        if (!session?.user) {
          router.push('/auth')
          return
        }

        setUser(session.user)

        // Check if user is a teacher
        const { data: teacherData } = await supabase
          .from('teachers')
          .select('id')
          .eq('id', session.user.id)
          .maybeSingle()

        if (teacherData) {
          setIsTeacher(true)
        } else {
          // Check if user is a student
          const { data: studentData } = await supabase
            .from('students')
            .select('user_id')
            .eq('user_id', session.user.id)
            .maybeSingle()

          if (studentData) {
            setIsTeacher(false)
          } else {
            // User not found in either table, auto-assign role
            await autoAssignRole(session.user)
            
            // Check again after auto-assignment
            const TEACHER_ID = 'e4bcab2f-8da5-4a78-85e8-094f4d7ac308'
            setIsTeacher(session.user.id === TEACHER_ID)
          }
        }
      } catch (error) {
        console.error('Error checking user role:', error)
        router.push('/auth')
      } finally {
        setLoading(false)
      }
    }

    if (mounted) {
      checkUserAndRole()
    }

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        router.push('/auth')
      }
    })

    return () => subscription.unsubscribe()
  }, [mounted, router])

  if (!mounted || loading) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar user={user} />
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-gray-900 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600">Loading your dashboard...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!user || isTeacher === null) {
    return null // Will redirect
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      <Navbar user={user} />
      <div className="flex-1">
        <ChatInterface user={user} isTeacher={isTeacher} />
      </div>
    </div>
  )
}