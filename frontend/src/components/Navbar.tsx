'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { User } from '@supabase/supabase-js'
import { LogOut, Menu, X, Calendar, Home } from 'lucide-react'

interface NavbarProps {
  user?: User | null
}

export default function Navbar({ user }: NavbarProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const router = useRouter()

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut()
      router.push('/')
      window.location.reload()
    } catch (error) {
      console.error('Logout error:', error)
      router.push('/')
      window.location.reload()
    }
  }

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <Link href="/" className="text-xl font-bold text-gray-900">
              LinkCode Scheduler
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link 
              href="/" 
              className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium"
            >
              Home
            </Link>
            
            {user && (
              <Link 
                href="/dashboard" 
                className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium"
              >
                Dashboard
              </Link>
            )}

            {user ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center">
                    <span className="text-white text-sm font-medium">
                      {user.user_metadata?.name?.charAt(0) || user.email?.charAt(0) || 'U'}
                    </span>
                  </div>
                  <span className="text-gray-700 text-sm font-medium">
                    {user.user_metadata?.name || user.email?.split('@')[0]}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium"
                >
                  Logout
                </button>
              </div>
            ) : (
              <Link
                href="/auth"
                className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-all duration-200 font-medium"
              >
                Sign in
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-600 hover:text-gray-900 transition-colors duration-200"
            >
              {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200 bg-white">
            <div className="flex flex-col space-y-4">
              <Link 
                href="/" 
                className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium px-2 py-1"
                onClick={() => setIsMenuOpen(false)}
              >
                Home
              </Link>
              
              {user && (
                <Link 
                  href="/dashboard" 
                  className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium px-2 py-1"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Dashboard
                </Link>
              )}

              {user ? (
                <div className="flex flex-col space-y-3 pt-3 border-t border-gray-200">
                  <div className="flex items-center space-x-2 px-2">
                    <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center">
                      <span className="text-white text-sm font-medium">
                        {user.user_metadata?.name?.charAt(0) || user.email?.charAt(0) || 'U'}
                      </span>
                    </div>
                    <span className="text-gray-700 text-sm font-medium">
                      {user.user_metadata?.name || user.email?.split('@')[0]}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      handleLogout()
                      setIsMenuOpen(false)
                    }}
                    className="text-gray-600 hover:text-gray-900 transition-colors duration-200 font-medium px-2 py-1 text-left"
                  >
                    Logout
                  </button>
                </div>
              ) : (
                <Link
                  href="/auth"
                  className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-all duration-200 font-medium mx-2 text-center"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Sign in
                </Link>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}