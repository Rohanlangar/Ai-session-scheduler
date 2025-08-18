import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
    try {
        const body = await request.json()
        const { teacher_id, filter_type = 'all' } = body

        if (!teacher_id) {
            return NextResponse.json(
                { success: false, error: 'Teacher ID is required' },
                { status: 400 }
            )
        }

        // Get backend URL from environment
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

        // Forward request to backend
        const response = await fetch(`${backendUrl}/api/teacher-sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                teacher_id,
                filter_type
            })
        })

        const result = await response.json()

        if (!response.ok) {
            throw new Error(result.error || 'Failed to fetch sessions')
        }

        return NextResponse.json(result)

    } catch (error) {
        console.error('Error in teacher-sessions API route:', error)
        return NextResponse.json(
            {
                success: false,
                error: error instanceof Error ? error.message : 'Internal server error',
                sessions: []
            },
            { status: 500 }
        )
    }
}