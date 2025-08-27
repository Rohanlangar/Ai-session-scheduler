'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Navbar from '@/components/Navbar'
import { Mail, Lock, Eye, EyeOff, ArrowLeft, Calendar, CheckCircle } from 'lucide-react'

export default function AuthPage() {
  const [user, setUser] = useState<User | null>(null)
  const [mounted, setMounted] = useState(false)
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [isSuccess, setIsSuccess] = useState(false)
  const router = useRouter()

  const autoAssignRole = async (user: User) => {
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
      // Don't throw error, just log it
    }
  }

  useEffect(() => {
    setMounted(true)
    
    // Check if user is already logged in and auto-assign role
    const getCurrentUser = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (session?.user) {
        // Auto-assign role and redirect to dashboard
        await autoAssignRole(session.user)
        setUser(session.user)
        router.push('/dashboard')
      }
    }
    
    getCurrentUser()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (session?.user) {
        // Auto-assign role and redirect
        await autoAssignRole(session.user)
        setUser(session.user)
        router.push('/dashboard')
      }
    })

    return () => subscription.unsubscribe()
  }, [router])

  if (!mounted) {
    return null
  }

  // If user is logged in, they will be redirected to dashboard automatically
  if (user) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-gray-900 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600">Setting up your account...</p>
        </div>
      </div>
    )
  }

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setIsSuccess(false)

    try {
      if (isLogin) {
        // Sign in
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })

        if (error) throw error

        // Auto-assign role for existing user if needed
        if (data.user) {
          await autoAssignRole(data.user)
        }

        setMessage('Successfully signed in!')
        setIsSuccess(true)
        
        // Redirect after a short delay
        setTimeout(() => {
          router.push('/dashboard')
        }, 1000)
      } else {
        // Sign up
        if (password !== confirmPassword) {
          throw new Error('Passwords do not match')
        }

        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`
          }
        })

        if (error) throw error

        // Check if email confirmation is required
        if (data.user && !data.session) {
          setMessage('Please check your email and click the confirmation link to complete signup.')
          setIsSuccess(true)
        } else if (data.user && data.session) {
          // Auto-assign role for new user (immediate signup without email confirmation)
          await autoAssignRole(data.user)
          setMessage('Account created successfully!')
          setIsSuccess(true)
          
          // Redirect after a short delay
          setTimeout(() => {
            router.push('/dashboard')
          }, 1500)
        }
      }
    } catch (error: any) {
      setMessage(error.message || 'An error occurred')
      setIsSuccess(false)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleAuth = async () => {
    try {
      setLoading(true)
      setMessage('')
      
      const redirectUrl = `${window.location.origin}/auth/callback`
      console.log('🔄 Starting Google OAuth with redirect:', redirectUrl)
      
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUrl,
        }
      })
      
      if (error) {
        console.error('OAuth error:', error)
        throw error
      }
      
      console.log('✅ OAuth initiated successfully')
    } catch (error: any) {
      console.error('Google auth error:', error)
      setMessage(error.message || 'Error signing in with Google')
      setIsSuccess(false)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar user={user} />
      
      <div className="flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          {/* Back to home */}
          <div className="mb-6">
            <Link 
              href="/" 
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors duration-200"
            >
              <ArrowLeft size={20} />
              <span>Back to Home</span>
            </Link>
          </div>

          {/* Auth Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center mx-auto mb-4">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {isLogin ? 'Welcome back' : 'Create account'}
              </h2>
              <p className="text-gray-600">
                {isLogin 
                  ? 'Sign in to your account' 
                  : 'Get started with LinkCode Scheduler'
                }
              </p>
            </div>

            {/* Toggle Login/Signup */}
            <div className="flex bg-gray-100 rounded-lg p-1 mb-6">
              <button
                onClick={() => {
                  setIsLogin(true)
                  setMessage('')
                  setEmail('')
                  setPassword('')
                  setConfirmPassword('')
                }}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ${
                  isLogin 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Sign in
              </button>
              <button
                onClick={() => {
                  setIsLogin(false)
                  setMessage('')
                  setEmail('')
                  setPassword('')
                  setConfirmPassword('')
                }}
                className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200 ${
                  !isLogin 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Sign up
              </button>
            </div>

            {/* Google Sign In */}
            <button
              onClick={handleGoogleAuth}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 bg-white border border-gray-200 rounded-lg px-6 py-3 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200 mb-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span className="text-gray-700 font-medium">
                Continue with Google
              </span>
            </button>

            {/* Divider */}
            <div className="relative mb-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">Or continue with email</span>
              </div>
            </div>

            {/* Email Form */}
            <form onSubmit={handleEmailAuth} className="space-y-4">
              {/* Email Input */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200"
                    placeholder="Enter your email"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full pl-10 pr-12 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200"
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-200"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {/* Confirm Password (Sign Up Only) */}
              {!isLogin && (
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                      id="confirmPassword"
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200"
                      placeholder="Confirm your password"
                    />
                  </div>
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-gray-900 text-white py-3 rounded-lg hover:bg-gray-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {loading ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{isLogin ? 'Signing in...' : 'Creating account...'}</span>
                  </div>
                ) : (
                  isLogin ? 'Sign in' : 'Create account'
                )}
              </button>
            </form>

            {/* Message */}
            {message && (
              <div className={`mt-4 p-4 rounded-xl flex items-center space-x-2 ${
                isSuccess 
                  ? 'bg-green-50 text-green-800 border border-green-200' 
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}>
                {isSuccess && <CheckCircle className="w-5 h-5" />}
                <span className="text-sm">{message}</span>
              </div>
            )}

            {/* Footer */}
            <div className="mt-6 text-center text-sm text-gray-600">
              {isLogin ? (
                <>
                  Don't have an account?{' '}
                  <button
                    onClick={() => {
                      setIsLogin(false)
                      setMessage('')
                    }}
                    className="text-gray-900 hover:text-gray-700 font-medium"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    onClick={() => {
                      setIsLogin(true)
                      setMessage('')
                    }}
                    className="text-gray-900 hover:text-gray-700 font-medium"
                  >
                    Sign in
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}