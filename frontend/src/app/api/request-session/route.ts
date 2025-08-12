import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { student_id, subject, date, start_time, end_time } = body

    // Call your Python backend
    const backendResponse = await fetch('http://localhost:8000/api/session-request', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        student_id,
        subject,
        date,
        start_time,
        end_time
      })
    })

    if (!backendResponse.ok) {
      throw new Error('Backend request failed')
    }

    const result = await backendResponse.json()
    return NextResponse.json(result)

  } catch (error) {
    console.error('Session request error:', error)
    return NextResponse.json(
      { error: 'Failed to process session request' },
      { status: 500 }
    )
  }
}