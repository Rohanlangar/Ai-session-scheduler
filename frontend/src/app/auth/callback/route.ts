import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')

  console.log('🔄 Auth callback triggered:', { code: !!code, error })

  if (error) {
    console.error('OAuth error:', error)
    return NextResponse.redirect(`${requestUrl.origin}?auth_error=${error}`)
  }

  if (code) {
    try {
      const supabase = createRouteHandlerClient({ cookies })
      const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
      
      if (exchangeError) {
        console.error('❌ Auth exchange error:', exchangeError)
        return NextResponse.redirect(`${requestUrl.origin}?auth_error=exchange_failed`)
      }
      
      if (data.user) {
        console.log('✅ Auth callback successful for user:', data.user.email)
        
        // Create student record if needed
        try {
          const { data: existingStudent } = await supabase
            .from('students')
            .select('user_id')
            .eq('user_id', data.user.id)
            .single()
          
          if (!existingStudent) {
            const userData = {
              user_id: data.user.id,
              name: data.user.user_metadata?.name || 
                    data.user.user_metadata?.full_name || 
                    data.user.email?.split('@')[0] || 
                    'Student',
              email: data.user.email
            }
            
            await supabase.from('students').insert(userData)
            console.log('✅ Student account created in callback')
          }
        } catch (studentError) {
          console.error('Student creation error (non-fatal):', studentError)
        }
        
        // Redirect to home with success
        return NextResponse.redirect(`${requestUrl.origin}?auth_success=true`)
      }
    } catch (error) {
      console.error('❌ Auth callback exception:', error)
      return NextResponse.redirect(`${requestUrl.origin}?auth_error=callback_exception`)
    }
  }

  console.log('🔄 Redirecting to home')
  return NextResponse.redirect(requestUrl.origin)
}