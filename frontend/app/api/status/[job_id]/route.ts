import type { NextRequest } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ job_id: string }> }) {
  const { job_id } = await params
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/status/${job_id}`)
    
    if (!response.ok) {
      return new Response(JSON.stringify({ error: "Not found" }), { status: 404 })
    }
    
    const data = await response.json()
    return new Response(JSON.stringify(data), { status: 200 })
  } catch (error) {
    return new Response(JSON.stringify({ error: "Backend connection failed" }), { status: 500 })
  }
}
