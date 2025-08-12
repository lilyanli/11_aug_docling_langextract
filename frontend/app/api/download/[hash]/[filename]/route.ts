import type { NextRequest } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ hash: string; filename: string }> }) {
  const { hash, filename } = await params
  
  try {
    const response = await fetch(`${BACKEND_URL}/api/download/${hash}/${filename}`)
    
    if (!response.ok) {
      return new Response(JSON.stringify({ error: "File not found" }), { status: 404 })
    }
    
    const content = await response.blob()
    const headers = new Headers()
    headers.set("Content-Type", response.headers.get("Content-Type") || "application/octet-stream")
    headers.set("Content-Disposition", `attachment; filename="${filename}"`)
    
    return new Response(content, {
      status: 200,
      headers,
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: "Backend connection failed" }), { status: 500 })
  }
}
