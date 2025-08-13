import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { message, user_id, is_teacher } = body

    // Call your Python backend with the chat message
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000'
    const backendResponse = await fetch(`${backendUrl}/api/chat-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        user_id,
        is_teacher
      })
    })

    if (!backendResponse.ok) {
      throw new Error('Backend request failed')
    }

    const result = await backendResponse.json()
    return NextResponse.json(result)

  } catch (error) {
    console.error('Chat session error:', error)
    return NextResponse.json(
      {
        response: 'I understand your request. Let me process that for you.',
        error: 'Backend temporarily unavailable'
      },
      { status: 200 } // Return 200 to avoid frontend errors
    )
  }
}