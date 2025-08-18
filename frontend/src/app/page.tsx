'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import Navbar from '@/components/Navbar'
import Link from 'next/link'
import { Calendar, Users, Clock, BookOpen, ArrowRight, CheckCircle, Star } from 'lucide-react'

export default function Home() {
  const [user, setUser] = useState<User | null>(null)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    
    // Get current user
    const getCurrentUser = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      setUser(session?.user || null)
    }
    
    getCurrentUser()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null)
    })

    return () => subscription.unsubscribe()
  }, [])

  if (!mounted) {
    return null
  }

  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      {/* Advanced Background Animation System */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Aurora-like gradient waves */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-blue-100 via-purple-50 to-pink-100 aurora-effect"></div>
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-l from-indigo-100 via-blue-50 to-cyan-100 aurora-effect" style={{ animationDelay: '4s' }}></div>
        </div>

        {/* Liquid morphing shapes */}
        <div className="absolute -top-32 -right-32 w-64 h-64 bg-gradient-to-br from-gray-100 to-gray-200 liquid-morph opacity-30"></div>
        <div className="absolute top-1/3 -left-32 w-48 h-48 bg-gradient-to-tr from-gray-50 to-gray-100 liquid-morph opacity-25" style={{ animationDelay: '6s' }}></div>
        <div className="absolute bottom-10 right-1/4 w-32 h-32 bg-gradient-to-bl from-gray-100 to-gray-200 liquid-morph opacity-20" style={{ animationDelay: '12s' }}></div>

        {/* Geometric dancing elements */}
        <div className="absolute top-1/4 left-1/6 w-8 h-8 bg-gray-200 geometric-dance opacity-25"></div>
        <div className="absolute top-2/3 right-1/5 w-6 h-6 bg-gray-300 geometric-dance opacity-30" style={{ animationDelay: '3s' }}></div>
        <div className="absolute bottom-1/4 left-1/3 w-10 h-10 bg-gray-100 geometric-dance opacity-20" style={{ animationDelay: '7s' }}></div>

        {/* Particle orbit system */}
        <div className="absolute top-1/2 left-1/2 w-2 h-2">
          <div className="absolute w-2 h-2 bg-blue-200 rounded-full particle-orbit opacity-40"></div>
          <div className="absolute w-1.5 h-1.5 bg-purple-200 rounded-full particle-orbit opacity-35" style={{ animationDelay: '5s' }}></div>
          <div className="absolute w-1 h-1 bg-pink-200 rounded-full particle-orbit opacity-30" style={{ animationDelay: '10s' }}></div>
        </div>

        {/* Spiral particle system */}
        <div className="absolute top-1/4 right-1/3 w-1 h-1">
          <div className="absolute w-2 h-2 bg-indigo-200 rounded-full particle-spiral opacity-35"></div>
          <div className="absolute w-1.5 h-1.5 bg-cyan-200 rounded-full particle-spiral opacity-30" style={{ animationDelay: '3s' }}></div>
        </div>

        {/* Wave motion elements */}
        <div className="absolute bottom-0 left-0 w-full h-32 opacity-10">
          <div className="absolute bottom-0 w-full h-8 bg-gradient-to-r from-transparent via-gray-300 to-transparent wave-motion"></div>
          <div className="absolute bottom-4 w-full h-6 bg-gradient-to-r from-transparent via-gray-400 to-transparent wave-motion" style={{ animationDelay: '2s' }}></div>
        </div>

        {/* Energy pulse elements */}
        <div className="absolute top-1/3 left-1/4 w-4 h-4 bg-blue-100 rounded-full energy-pulse opacity-40"></div>
        <div className="absolute bottom-1/3 right-1/4 w-3 h-3 bg-purple-100 rounded-full energy-pulse opacity-35" style={{ animationDelay: '2s' }}></div>

        {/* Floating gradient orbs */}
        <div className="absolute top-20 left-1/5 w-16 h-16 bg-gradient-to-br from-blue-100 to-purple-100 rounded-full bg-animate-float-slow opacity-20"></div>
        <div className="absolute bottom-32 right-1/6 w-12 h-12 bg-gradient-to-tr from-pink-100 to-indigo-100 rounded-full bg-animate-float-medium opacity-25" style={{ animationDelay: '4s' }}></div>
        <div className="absolute top-1/2 right-10 w-20 h-20 bg-gradient-to-bl from-cyan-100 to-blue-100 rounded-full bg-animate-drift opacity-15" style={{ animationDelay: '8s' }}></div>

        {/* Moving gradient overlays */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-gray-50 to-transparent opacity-20 animate-gradient-x"></div>
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-gray-50 to-transparent opacity-15 animate-gradient-y" style={{ animationDelay: '5s' }}></div>

        {/* Subtle grid pattern */}
        <div className="absolute inset-0 opacity-5" style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(0,0,0,0.15) 1px, transparent 0)`,
          backgroundSize: '20px 20px'
        }}></div>
      </div>

      <div className="relative z-10">
        <Navbar user={user} />
        
        {/* Hero Section */}
        <section className="relative overflow-hidden">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
            <div className="text-center">
            <div className="mb-8">
              <div className="inline-flex items-center space-x-2 bg-gray-50 border border-gray-200 px-4 py-2 rounded-full text-sm font-medium text-gray-600 mb-8">
                <Star className="w-4 h-4" />
                <span>AI-Powered Session Scheduling</span>
              </div>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold mb-8 text-gray-900 leading-tight">
              The AI session scheduler
              <br />
              <span className="text-gray-600">for modern education</span>
            </h1>
            
            <p className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed">
              Connect students and teachers seamlessly with intelligent scheduling. 
              Book sessions, set availability, and optimize learning outcomes.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              {user ? (
                <Link
                  href="/dashboard"
                  className="bg-black text-white px-8 py-4 rounded-lg hover:bg-gray-800 transition-all duration-300 flex items-center space-x-2 text-lg font-medium hover-lift"
                >
                  <Calendar className="w-5 h-5" />
                  <span>Go to Dashboard</span>
                  <ArrowRight className="w-5 h-5" />
                </Link>
              ) : (
                <>
                  <Link
                    href="/auth"
                    className="bg-black text-white px-8 py-4 rounded-lg hover:bg-gray-800 transition-all duration-300 flex items-center space-x-2 text-lg font-medium hover-lift"
                  >
                    <span>Get started</span>
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                  <Link
                    href="#features"
                    className="text-gray-600 px-8 py-4 rounded-lg border border-gray-200 hover:border-gray-300 hover:bg-gray-50 transition-all duration-300 flex items-center space-x-2 text-lg font-medium hover-lift"
                  >
                    <span>Learn more</span>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Why choose LinkCode Scheduler?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Experience the future of educational scheduling with our AI-powered platform
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8 rounded-xl bg-white border border-gray-200 hover:shadow-lg transition-all duration-300 hover-lift">
              <div className="w-16 h-16 bg-gray-900 rounded-xl flex items-center justify-center mx-auto mb-6">
                <Calendar className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Smart Scheduling</h3>
              <p className="text-gray-600 leading-relaxed">
                AI-powered scheduling that finds the perfect time slots for both students and teachers automatically.
              </p>
            </div>
            
            <div className="text-center p-8 rounded-xl bg-white border border-gray-200 hover:shadow-lg transition-all duration-300 hover-lift">
              <div className="w-16 h-16 bg-gray-900 rounded-xl flex items-center justify-center mx-auto mb-6">
                <Users className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Easy Collaboration</h3>
              <p className="text-gray-600 leading-relaxed">
                Connect students and teachers seamlessly with instant notifications and real-time updates.
              </p>
            </div>
            
            <div className="text-center p-8 rounded-xl bg-white border border-gray-200 hover:shadow-lg transition-all duration-300 hover-lift">
              <div className="w-16 h-16 bg-gray-900 rounded-xl flex items-center justify-center mx-auto mb-6">
                <Clock className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-4">Time Optimization</h3>
              <p className="text-gray-600 leading-relaxed">
                Optimize session timings based on everyone's availability and preferences automatically.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              How it works
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Get started in just a few simple steps
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold">1</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Sign up & choose role</h3>
                  <p className="text-gray-600 leading-relaxed">Create your account and select whether you're a student or teacher.</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold">2</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Set preferences</h3>
                  <p className="text-gray-600 leading-relaxed">Tell our AI about your availability, subjects, and scheduling preferences.</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-white font-bold">3</span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">AI magic</h3>
                  <p className="text-gray-600 leading-relaxed">Our AI finds the perfect matches and schedules sessions automatically.</p>
                </div>
              </div>
              
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center flex-shrink-0">
                  <CheckCircle className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Start learning</h3>
                  <p className="text-gray-600 leading-relaxed">Join your scheduled sessions and focus on what matters - learning!</p>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-8">
              <div className="bg-gray-900 rounded-xl p-6 text-white mb-6">
                <Calendar className="w-12 h-12 mb-4" />
                <h3 className="text-2xl font-bold mb-2">Ready to get started?</h3>
                <p className="text-gray-300">Join thousands of students and teachers already using LinkCode Scheduler.</p>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-gray-700">Free to get started</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-gray-700">AI-powered matching</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-gray-700">Real-time notifications</span>
                </div>
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-gray-700">24/7 support</span>
                </div>
              </div>
              
              {!user && (
                <Link
                  href="/auth"
                  className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-all duration-200 flex items-center justify-center space-x-2 font-medium mt-6"
                >
                  <span>Get started now</span>
                  <ArrowRight className="w-5 h-5" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 border-t border-gray-200 py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="flex items-center justify-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-gray-900 rounded-lg flex items-center justify-center">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900">
                LinkCode Scheduler
              </span>
            </div>
            <p className="text-gray-600 mb-6">
              Connecting students and teachers through intelligent scheduling
            </p>
            <div className="border-t border-gray-200 pt-6">
              <p className="text-gray-500 text-sm">
                © 2025 LinkCode Scheduler. All rights reserved.
              </p>
            </div>
          </div>
        </div>
      </footer>
      </div>
    </div>
  )
}