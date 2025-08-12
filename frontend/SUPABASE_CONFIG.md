# Supabase Configuration for Production

## CRITICAL: Update these settings in your Supabase Dashboard

### 1. Authentication → URL Configuration
- **Site URL:** `https://ai-session-scheduler-vr6n.vercel.app`
- **Redirect URLs:** Add ALL of these:
  - `https://ai-session-scheduler-vr6n.vercel.app`
  - `https://ai-session-scheduler-vr6n.vercel.app/auth/callback`
  - `https://ai-session-scheduler-vr6n.vercel.app/**`

### 2. Authentication → Providers → Google
- Make sure Google OAuth is enabled
- **Authorized redirect URIs** should include:
  - `https://ipfzpnxdtackprxforqh.supabase.co/auth/v1/callback`

### 3. Database → RLS Policies
Make sure your tables have proper RLS policies or are accessible.

## Testing Steps:
1. Clear browser cache and cookies
2. Try incognito/private browsing
3. Check browser console for errors
4. Verify the redirect URLs match exactly

## Common Issues:
- Redirect URL mismatch (case sensitive)
- Missing trailing slashes
- Wrong domain in Supabase settings
- RLS blocking database access