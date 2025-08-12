import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

// Provide fallback values for build time
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://placeholder.supabase.co'
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'placeholder-key'

export const supabase = createClientComponentClient({
  supabaseUrl,
  supabaseKey
})