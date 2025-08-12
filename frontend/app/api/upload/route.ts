import type { NextRequest } from "next/server"

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData()
    const file = formData.get("file") as File | null
    const hash = (formData.get("hash") as string) || ""
    if (!file || !hash) {
      return new Response(JSON.stringify({ error: "file and hash required" }), { status: 400 })
    }

    // Forward the file to the backend
    const backendFormData = new FormData()
    backendFormData.append("file", file)

    const response = await fetch(`${BACKEND_URL}/api/upload`, {
      method: 'POST',
      body: backendFormData,
    })

    if (!response.ok) {
      const errorText = await response.text()
      return new Response(JSON.stringify({ error: `Backend upload failed: ${errorText}` }), { status: response.status })
    }

    const data = await response.json()
    return new Response(JSON.stringify({ job_id: data.job_id, doc_type: data.doc_type }), { status: 200 })
  } catch (e: any) {
    console.error("Upload route error:", e)
    return new Response(JSON.stringify({ error: `Upload failed: ${e.message || e.toString()}` }), { status: 500 })
  }
}
