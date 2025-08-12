"use client"

import type React from "react"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { useDropzone } from "react-dropzone"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"
import { computeSHA256Hex } from "@/lib/crypto"
import {
  CheckCircle2,
  Clipboard,
  ClipboardCheck,
  Download,
  FileDown,
  FileUp,
  HistoryIcon,
  Info,
  LinkIcon,
  Loader2,
  Sparkles,
  XCircle,
  Edit3,
  Save,
  X,
} from "lucide-react"

type DocType = "fund_financials" | "investor_report" | "generic"

type StatusState = "queued" | "processing" | "extracting" | "done" | "error"

type StatusResponse = {
  job_id: string
  state: StatusState
  progress: number
  message?: string
  entities?: Record<string, any> | null
  downloads?: Record<string, string> | null
  preview?: any | null
  doc_type?: DocType
  hash?: string
}

type ResultResponse = {
  hash: string
  filename: string
  doc_type: DocType
  entities: Record<string, any> | null
  downloads: Record<string, string>
  preview: any | null
  completedAt?: string
}

type HistoryItem = {
  hash: string
  filename: string
  doc_type: DocType
  completedAt: string
  downloads: Record<string, string>
}

export default function UploadPage() {
  const { toast } = useToast()

  const [file, setFile] = useState<File | null>(null)
  const [hash, setHash] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [docType, setDocType] = useState<DocType | null>(null)
  const [progress, setProgress] = useState<number>(0)
  const [state, setState] = useState<StatusState>("queued")
  const [statusMessage, setStatusMessage] = useState<string>("Waiting for upload")
  const [entities, setEntities] = useState<Record<string, any> | null>(null)
  const [downloads, setDownloads] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState<any | null>(null)

  const [editedPreview, setEditedPreview] = useState<any | null>(null)
  const [finalConfirmed, setFinalConfirmed] = useState<boolean>(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [confirmationDialogOpen, setConfirmationDialogOpen] = useState<boolean>(false)

  const [history, setHistory] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState<boolean>(false)

  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const copyTimerRef = useRef<NodeJS.Timeout | null>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const [previewPanelOpen, setPreviewPanelOpen] = useState<boolean>(false)
  const [previewData, setPreviewData] = useState<{
    filename: string
    entities: Record<string, any> | null
    preview: any | null
    doc_type: DocType
    completedAt: string
  } | null>(null)

  // Custom polling hook replacement
  const pollStatus = useCallback(async () => {
    if (!jobId) return

    try {
      const res = await fetch(`/api/status/${jobId}`)
      if (!res.ok) throw new Error("Failed to fetch status")
      const data: StatusResponse = await res.json()

      if (data.doc_type && !docType) setDocType(data.doc_type)
      if (data.hash && !hash) setHash(data.hash)
      setProgress(data.progress ?? 0)
      setState(data.state)
      setStatusMessage(
        data.message ??
          (data.state === "queued"
            ? "Queued"
            : data.state === "processing"
              ? "Processing..."
              : data.state === "extracting"
                ? "Extracting entities..."
                : data.state === "done"
                  ? "Completed"
                  : "Error"),
      )

      // When entities arrive, set them directly without opening dialog
      if (data.entities) {
        setEntities((prev) => prev ?? data.entities ?? null)
      }

      if (data.state === "done") {
        if (data.downloads) setDownloads(data.downloads)
        if (data.preview) setPreview(data.preview)
        if (data.preview && !editedPreview) setEditedPreview(data.preview)
        if (!sessionId) setSessionId(`session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`)
        // refresh history
        loadHistory()
      }

      // Continue polling if not done or error
      if (data.state !== "done" && data.state !== "error") {
        pollIntervalRef.current = setTimeout(pollStatus, 1500)
      }
    } catch (error) {
      console.error("Status polling error:", error)
      // Continue polling on error
      pollIntervalRef.current = setTimeout(pollStatus, 1500)
    }
  }, [jobId, docType, hash, editedPreview, sessionId])

  // Start polling when jobId is set
  useEffect(() => {
    if (jobId) {
      pollStatus()
    }
    return () => {
      if (pollIntervalRef.current) {
        clearTimeout(pollIntervalRef.current)
      }
    }
  }, [jobId, pollStatus])

  // Load history
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const res = await fetch("/api/history?limit=5")
      if (res.ok) {
        const data: { items: HistoryItem[] } = await res.json()
        setHistory(data.items)
      }
    } catch (error) {
      console.error("Failed to load history:", error)
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  // Load history on mount
  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  const handleDocumentPreview = async (hash: string, filename: string, doc_type: DocType, completedAt: string) => {
    try {
      const res = await fetch(`/api/result/${encodeURIComponent(hash)}`)
      if (res.ok) {
        const result: ResultResponse = await res.json()
        setPreviewData({
          filename,
          entities: result.entities,
          preview: result.preview,
          doc_type,
          completedAt,
        })
        setPreviewPanelOpen(true)
      } else {
        toast({ variant: "destructive", description: "Failed to load document preview" })
      }
    } catch (error) {
      toast({ variant: "destructive", description: "Error loading document preview" })
    }
  }

  // Dropzone setup
  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles.length) return
      const f = acceptedFiles[0]
      setFile(f)
  
      setDownloads({})
      setPreview(null)
      setEditedPreview(null)
      setFinalConfirmed(false)
      setSessionId(null)
      setProgress(0)
      setState("queued")
      setStatusMessage("Computing file fingerprint...")

      try {
        // Compute SHA-256
        const h = await computeSHA256Hex(f)
        setHash(h)

        // Check if result already exists
        const resultRes = await fetch(`/api/result/${encodeURIComponent(h)}`)
        if (resultRes.ok) {
          const result: ResultResponse = await resultRes.json()
          hydrateFromResult(result)
          toast({ description: "Matched an existing result. Skipped upload." })
          return
        }

        // Otherwise upload
        setStatusMessage("Uploading file...")
        const fd = new FormData()
        fd.append("file", f)
        fd.append("hash", h)
        const uploadRes = await fetch("/api/upload", {
          method: "POST",
          body: fd,
        })
        if (!uploadRes.ok) {
          throw new Error(`Upload failed (${uploadRes.status})`)
        }
        const uploadData: { job_id: string; doc_type: DocType } = await uploadRes.json()
        setJobId(uploadData.job_id)
        setDocType(uploadData.doc_type)
        setStatusMessage("File uploaded. Starting processing...")
        setProgress(10)
        setState("processing")
        toast({ description: "Upload successful. Processing started." })
      } catch (err: any) {
        console.error(err)
        setStatusMessage("Upload failed")
        setState("error")
        toast({
          variant: "destructive",
          description: "Upload failed. Please try again.",
        })
      }
    },
    [toast],
  )

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    open: openFileDialog,
  } = useDropzone({
    onDrop,
    multiple: false,
    noClick: true,
    accept: {
      "application/pdf": [".pdf"],
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/json": [".json"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
  })

  function hydrateFromResult(result: ResultResponse) {
    setDocType(result.doc_type)
    setEntities(result.entities ?? null)
    setDownloads(result.downloads || {})
    setPreview(result.preview ?? null)
    setEditedPreview(result.preview ?? null)  // This was missing!
    setProgress(100)
    setState("done")
    setStatusMessage("Completed")
  }

  function resetAll() {
    setFile(null)
    setHash(null)
    setJobId(null)
    setDocType(null)
    setProgress(0)
    setState("queued")
    setStatusMessage("Waiting for upload")
    setEntities(null)
    setDownloads({})
    setPreview(null)
    setEditedPreview(null)
    setFinalConfirmed(false)
    setSessionId(null)
    setConfirmationDialogOpen(false)
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current)
    }
  }

  const steps = useMemo(
    () => [
      { key: "uploaded", label: "Uploaded", done: !!file },
      {
        key: "processing",
        label: "Processing",
        done: state === "processing" || state === "extracting" || state === "done",
      },
      { key: "done", label: "Done", done: state === "done" },
    ],
    [file, state],
  )

  const isDone = state === "done"
  const isError = state === "error"



  async function copyLink(url: string, key: string) {
    try {
      await navigator.clipboard.writeText(url)
      setCopiedKey(key)
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current)
      copyTimerRef.current = setTimeout(() => setCopiedKey(null), 1500)
      toast({ description: "Link copied to clipboard." })
    } catch {
      toast({ variant: "destructive", description: "Failed to copy link." })
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col items-start justify-between gap-4 border-b border-border/40 pb-6 sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <img src="/logo.jpg" alt="Instella" className="h-24 w-auto" />
            <div className="h-16 w-px bg-border/60"></div>
          </div>
          <div className="space-y-1">
            <h1 className="text-3xl font-light tracking-tight text-foreground">Document Intelligence</h1>
            <p className="text-base text-muted-foreground/80">Structure the Unstructured</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 rounded-full bg-muted/50 px-3 py-1.5 text-xs font-medium text-muted-foreground">
            <div className="h-1.5 w-1.5 rounded-full bg-green-500"></div>
            System Online
          </div>
          <Link
            href="https://ui.shadcn.com"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
          >
            <Info className="mr-1.5 h-3.5 w-3.5" />
            Documentation
          </Link>
        </div>
      </header>

      {/* Grid */}
      <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
        {/* Left column */}
        <div className="space-y-6">
          {/* Dropzone Card */}
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm" aria-labelledby="dropzone-title">
            <CardHeader className="pb-4">
              <CardTitle id="dropzone-title" className="flex items-center gap-2.5 text-lg font-medium">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
                  <FileUp className="h-4 w-4 text-primary" />
                </div>
                Upload Document
              </CardTitle>
              <CardDescription className="text-sm text-muted-foreground/70">
                Supports PDF, CSV, XLSX, JSON, and image formats up to 50MB
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div
                {...getRootProps()}
                className={cn(
                  "group relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-border/60 bg-muted/20 p-8 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                  isDragActive
                    ? "border-primary/60 bg-primary/5 shadow-lg shadow-primary/10"
                    : "hover:border-border/80 hover:bg-muted/30",
                )}
                aria-label="File dropzone"
              >
                <input {...getInputProps()} aria-label="Choose file" />
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-background shadow-sm ring-1 ring-border/50 group-hover:shadow-md transition-shadow">
                  <FileUp
                    className={cn("h-5 w-5 transition-colors", isDragActive ? "text-primary" : "text-muted-foreground")}
                  />
                </div>
                <div className="mt-4 text-center">
                  <p className="text-sm font-medium text-foreground">
                    {isDragActive ? "Drop your file here" : "Drag & drop your document"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground/70">or click to browse files</p>
                </div>
                <div className="mt-6">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="bg-background shadow-sm hover:shadow-md transition-shadow"
                    onClick={openFileDialog}
                  >
                    Browse Files
                  </Button>
                </div>
                {file && (
                  <div className="mt-6 w-full max-w-sm rounded-lg border border-border/50 bg-background/80 p-4 shadow-sm backdrop-blur-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-foreground" title={file.name}>
                          {file.name}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      </div>
                      <Badge
                        variant="secondary"
                        className="shrink-0 bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300"
                      >
                        Ready
                      </Badge>
                    </div>
                    {hash && (
                      <div className="mt-3 flex items-center gap-2 rounded-md bg-muted/50 p-2 text-xs">
                        <LinkIcon className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="font-mono text-muted-foreground" title={hash}>
                          {hash.slice(0, 16)}...
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div className="mt-4 flex items-center justify-between">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={resetAll}
                  disabled={!file && !hash && !jobId}
                  className="text-muted-foreground hover:text-foreground"
                >
                  Reset
                </Button>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="h-1 w-1 rounded-full bg-muted-foreground/50"></div>
                  <span>Secure processing</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Status Card */}
          <Card
            className="border-border/50 bg-card/50 backdrop-blur-sm"
            aria-live="polite"
            aria-busy={state !== "done" && state !== "error"}
          >
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2.5 text-lg font-medium">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-lg transition-colors",
                    isError
                      ? "bg-destructive/10 text-destructive"
                      : isDone
                        ? "bg-green-50 text-green-600 dark:bg-green-950 dark:text-green-400"
                        : "bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-400",
                  )}
                >
                  {isError ? (
                    <XCircle className="h-4 w-4" />
                  ) : isDone ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                </div>
                Processing Status
              </CardTitle>
              <div className="flex items-center gap-3">
                <CardDescription className="text-sm text-muted-foreground/80">{statusMessage}</CardDescription>
                {docType && (
                  <Badge variant="outline" className="bg-background/50 text-xs font-medium">
                    {docType.replace("_", " ").toUpperCase()}
                  </Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-medium tabular-nums">{progress}%</span>
                  </div>
                  <Progress value={progress} className="h-2 bg-muted/50" aria-label="Processing progress" />
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {steps.map((s, index) => (
                    <div
                      key={s.key}
                      className={cn(
                        "relative flex items-center gap-2.5 rounded-lg border p-3 text-sm transition-all",
                        s.done
                          ? "border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200"
                          : "border-border/50 bg-muted/30 text-muted-foreground",
                      )}
                    >
                      <div
                        className={cn(
                          "flex h-5 w-5 items-center justify-center rounded-full border text-xs font-medium transition-colors",
                          s.done
                            ? "border-green-300 bg-green-100 text-green-700 dark:border-green-700 dark:bg-green-900 dark:text-green-300"
                            : "border-border bg-background text-muted-foreground",
                        )}
                      >
                        {s.done ? <CheckCircle2 className="h-3 w-3" /> : <span className="text-xs">{index + 1}</span>}
                      </div>
                      <span className="font-medium">{s.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Preview Card */}
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2.5 text-xl font-medium">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-50 dark:bg-purple-950">
                  <Sparkles className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                </div>
                Data Preview
              </CardTitle>
              <CardDescription className="text-sm text-muted-foreground/70">
                Extracted content and insights
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              {!editedPreview ? (
                <div className="flex items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/20 p-8">
                  <div className="text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted/50">
                      <Sparkles className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <p className="mt-3 text-sm text-muted-foreground/70">Preview will appear here</p>
                  </div>
                </div>
              ) : (
                <FundDataPreview
                  entities={entities}
                  preview={editedPreview}
                  onUpdate={setEditedPreview}
                  sessionId={sessionId}
                />
              )}
            </CardContent>
          </Card>

          {/* Final Confirmation Card */}
          {preview && !finalConfirmed && (
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2.5 text-lg font-medium">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 dark:bg-green-950">
                    <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  </div>
                  Final Confirmation
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground/70">
                  Review your edited data and confirm to generate outputs
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-4">
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-950">
                    <div className="flex items-start gap-3">
                      <Info className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                          Ready for Final Confirmation
                        </p>
                        <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                          Please review your edited data above. Once confirmed, session-specific output files will be
                          generated.
                        </p>
                      </div>
                    </div>
                  </div>
                  <Button onClick={() => setConfirmationDialogOpen(true)} className="w-full shadow-sm" size="lg">
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Confirm & Generate Outputs
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Downloads Card */}
          {finalConfirmed && (
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2.5 text-lg font-medium">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950">
                    <FileDown className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  </div>
                  Session Downloads
                </CardTitle>
                <CardDescription className="text-sm text-muted-foreground/70">
                  Generated files for session: {sessionId}
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                {Object.keys(downloads).length === 0 ? (
                  <div className="flex items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/20 p-6">
                    <p className="text-sm text-muted-foreground/70">No downloads available yet</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {Object.entries(downloads).map(([key, url]) => {
                      const sessionUrl = `${url}?session=${sessionId}&timestamp=${Date.now()}`
                      return (
                        <div
                          key={key}
                          className="flex items-center justify-between rounded-lg border border-border/50 bg-background/50 p-3"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted/50">
                              <Download className="h-4 w-4 text-muted-foreground" />
                            </div>
                            <div>
                              <p className="text-sm font-medium">{key.toUpperCase()}</p>
                              <p className="text-xs text-muted-foreground">Session: {sessionId?.slice(-8)}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button asChild size="sm" className="shadow-sm">
                              <a href={sessionUrl} target="_blank" rel="noreferrer" aria-label={`Download ${key}`}>
                                <Download className="mr-1.5 h-3.5 w-3.5" />
                                Download
                              </a>
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              aria-label={`Copy ${key} link`}
                              onClick={() => copyLink(sessionUrl, key)}
                              className="h-8 w-8 p-0"
                            >
                              {copiedKey === key ? (
                                <ClipboardCheck className="h-3.5 w-3.5 text-green-600" />
                              ) : (
                                <Clipboard className="h-3.5 w-3.5" />
                              )}
                            </Button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* History Card */}
          <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2.5 text-lg font-medium">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-950">
                  <HistoryIcon className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                </div>
                Recent Activity
              </CardTitle>
              <CardDescription className="text-sm text-muted-foreground/70">
                Previously processed documents
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              {historyLoading ? (
                <div className="flex items-center gap-3 rounded-lg bg-muted/20 p-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Loading history...</span>
                </div>
              ) : history.length > 0 ? (
                <div className="space-y-3">
                  {history.map((item) => (
                    <div
                      key={item.hash}
                      className="rounded-lg border border-border/50 bg-background/50 p-4 cursor-pointer hover:bg-muted/20 transition-colors"
                      onClick={() => handleDocumentPreview(item.hash, item.filename, item.doc_type, item.completedAt)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <p
                            className="truncate text-sm font-medium text-foreground hover:text-primary transition-colors"
                            title={item.filename}
                          >
                            {item.filename}
                          </p>
                          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                            <Badge variant="outline" className="bg-background/50 text-xs">
                              {item.doc_type.replace("_", " ").toUpperCase()}
                            </Badge>
                            <span>{new Date(item.completedAt).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          {Object.entries(item.downloads).map(([key, url]) => (
                            <Button
                              key={key}
                              asChild
                              size="sm"
                              variant="secondary"
                              className="h-7 text-xs"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <a href={url} target="_blank" rel="noreferrer" aria-label={`Download ${key}`}>
                                <Download className="mr-1 h-3 w-3" />
                                {key.toUpperCase()}
                              </a>
                            </Button>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/20 p-6">
                  <div className="text-center">
                    <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-muted/50">
                      <HistoryIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground/70">No history yet</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>



      {/* Final Confirmation Dialog */}
      <Dialog open={confirmationDialogOpen} onOpenChange={setConfirmationDialogOpen}>
        <DialogContent className="max-w-lg border-border/50 bg-card/95 backdrop-blur-sm">
          <DialogHeader className="space-y-3">
            <DialogTitle className="flex items-center gap-2.5 text-xl font-medium">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-green-50 dark:bg-green-950">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
              </div>
              Confirm Final Data
            </DialogTitle>
            <DialogDescription className="text-muted-foreground/80">
              You are about to confirm the processed data and generate session-specific output files. This action will
              finalize your edits and make the data available for download.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-lg border border-border/50 bg-muted/20 p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950">
                  <FileDown className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-medium">Session ID</p>
                  <p className="text-xs text-muted-foreground font-mono">{sessionId}</p>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setConfirmationDialogOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                setFinalConfirmed(true)
                setConfirmationDialogOpen(false)
                toast({ description: "Data confirmed! Session-specific downloads are now available." })
              }}
              className="shadow-sm"
            >
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Confirm & Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Preview Panel */}
      <Dialog open={previewPanelOpen} onOpenChange={setPreviewPanelOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] border-border/50 bg-card/95 backdrop-blur-sm">
          <DialogHeader className="space-y-3">
            <DialogTitle className="flex items-center gap-2.5 text-xl font-medium">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-50 dark:bg-purple-950">
                <Sparkles className="h-4 w-4 text-purple-600 dark:text-purple-400" />
              </div>
              Document Preview
            </DialogTitle>
            <DialogDescription className="text-muted-foreground/80">
              {previewData?.filename} • Processed on{" "}
              {previewData?.completedAt ? new Date(previewData.completedAt).toLocaleDateString() : "Unknown"}
            </DialogDescription>
          </DialogHeader>

          <div className="overflow-y-auto max-h-[70vh] pr-2">
            {previewData && (
              <FundDataPreview
                entities={previewData.entities}
                preview={previewData.preview}
                onUpdate={() => {}} // Read-only in preview mode
                sessionId={null} // No session ID for historical previews
                readOnly={true}
              />
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setPreviewPanelOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function FundDataPreview({
  entities,
  preview,
  onUpdate,
  sessionId,
  readOnly = false,
}: {
  entities: Record<string, any> | null
  preview: any
  onUpdate: (newPreview: any) => void
  sessionId: string | null
  readOnly?: boolean
}) {
  const { toast } = useToast()

  return (
    <div className="space-y-6">
      {/* Fund Information Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground">{preview?.fund?.name || entities?.fund_name || "Fund Name"}</h3>
            <p className="text-sm text-muted-foreground">
              Reporting Period:{" "}
              {preview?.fund?.reporting_period 
                ? preview.fund.reporting_period
                : entities?.period_start && entities?.period_end
                  ? `${new Date(entities.period_start).toLocaleDateString()} - ${new Date(entities.period_end).toLocaleDateString()}`
                  : entities?.fiscal_year
                    ? `Fiscal Year ${entities.fiscal_year}`
                    : "Not specified"}
            </p>
          </div>
        </div>
      </div>

      {/* Schedule of Investments Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-base font-medium text-foreground">Schedule of Investments</h4>
          <Badge variant="secondary" className="bg-background/50 text-xs">
            {preview?.soi?.length || 0} investments
          </Badge>
        </div>

        {!preview?.soi || preview.soi.length === 0 ? (
          <div className="flex items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/20 p-8">
            <p className="text-sm text-muted-foreground/70">No investment data found</p>
          </div>
        ) : (
          <EditableInvestmentsTable
            investments={preview.soi}
            onUpdate={readOnly ? () => {} : (newInvestments) => onUpdate({ ...preview, soi: newInvestments })}
            readOnly={readOnly}
          />
        )}
      </div>
    </div>
  )
}

// Helper function to format cell values
function formatCellValue(value: any, column: string): string {
  if (value === null || value === undefined) return ""
  
  // Format numbers with commas for thousands
  if (typeof value === 'number') {
    // Special formatting for ownership percentages
    if (column.toLowerCase().includes('ownership')) {
      return `${value.toFixed(2)}%`
    }
    
    // Check if it's a currency/numeric column
    if (column.toLowerCase().includes('cost') || 
        column.toLowerCase().includes('value') || 
        column.toLowerCase().includes('fair') ||
        column.toLowerCase().includes('shares') ||
        column.toLowerCase().includes('moic')) {
      return value.toLocaleString('en-US', { 
        minimumFractionDigits: 0,
        maximumFractionDigits: 2 
      })
    }
    return value.toString()
  }
  
  return String(value)
}

function EditableInvestmentsTable({
  investments,
  onUpdate,
  readOnly = false,
}: {
  investments: Array<Record<string, any>>
  onUpdate: (newInvestments: Array<Record<string, any>>) => void
  readOnly?: boolean
}) {
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null)
  const [editValue, setEditValue] = useState<string>("")

  const displayRows = investments.slice(0, 50) // Show up to 50 rows
  
  // Only show columns that have data in at least one row
  const allColumns = investments.length > 0 ? Object.keys(investments[0]) : []
  const columns = allColumns.filter(col => {
    return displayRows.some(row => {
      const value = row[col]
      return value !== null && value !== undefined && value !== ""
    })
  })

  const startEdit = (rowIndex: number, column: string, currentValue: any) => {
    setEditingCell({ row: rowIndex, col: column })
    setEditValue(String(currentValue ?? ""))
  }

  const saveEdit = () => {
    if (!editingCell) return

    const newInvestments = [...investments]
    newInvestments[editingCell.row] = {
      ...newInvestments[editingCell.row],
      [editingCell.col]: editValue,
    }

    onUpdate(newInvestments)
    setEditingCell(null)
    setEditValue("")
  }

  const cancelEdit = () => {
    setEditingCell(null)
    setEditValue("")
  }

  if (!columns.length) {
    return (
      <div className="flex items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/20 p-8">
        <p className="text-sm text-muted-foreground/70">No investment data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Badge variant="outline" className="bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300 text-xs">
          Click cells to edit • Showing {displayRows.length} of {investments.length} rows
        </Badge>
      </div>

      <div className="overflow-hidden rounded-lg border border-border/50">
        <div className="max-h-96 overflow-auto">
          <Table>
            <TableHeader className="bg-muted/30 sticky top-0">
              <TableRow className="border-border/50">
                {columns.map((col) => (
                  <TableHead key={col} className="whitespace-nowrap font-medium text-foreground min-w-[120px]">
                    {col === "interest_fee_receivable" ? "Interest/Fee Receivable" :
                     col === "currency_exposure" ? "Currency Exposure" :
                     col.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayRows.map((row: Record<string, any>, i) => (
                <TableRow key={i} className="border-border/30 hover:bg-muted/20">
                  {columns.map((col) => (
                    <TableCell key={col} className="whitespace-nowrap min-w-[120px]">
                      {!readOnly && editingCell?.row === i && editingCell?.col === col ? (
                        <div className="flex items-center gap-2">
                          <Input
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="h-8 text-sm min-w-[100px]"
                            onKeyDown={(e) => {
                              if (e.key === "Enter") saveEdit()
                              if (e.key === "Escape") cancelEdit()
                            }}
                            autoFocus
                          />
                          <Button size="sm" variant="ghost" onClick={saveEdit} className="h-6 w-6 p-0 shrink-0">
                            <Save className="h-3 w-3 text-green-600" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={cancelEdit} className="h-6 w-6 p-0 shrink-0">
                            <X className="h-3 w-3 text-red-600" />
                          </Button>
                        </div>
                      ) : (
                        <div
                          className={cn(
                            "group flex items-center gap-2 rounded px-2 py-1 -mx-2 -my-1 min-h-[32px]",
                            !readOnly && "cursor-pointer hover:bg-muted/30",
                          )}
                          onClick={!readOnly ? () => startEdit(i, col, row[col]) : undefined}
                        >
                          <span 
                            className={cn(
                              "text-sm flex-1 truncate font-['SF_Pro_Display']",
                              // Use monospace for numbers, regular font for text
                              typeof row[col] === 'number' ? "font-mono" : "font-['SF_Pro_Text']"
                            )} 
                            title={String(row[col] ?? "")}
                          >
                            {formatCellValue(row[col], col)}
                          </span>
                          {!readOnly && (
                            <Edit3 className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                          )}
                        </div>
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>

      {investments.length > displayRows.length && (
        <div className="text-center py-2">
          <Badge variant="secondary" className="text-xs">
            Showing {displayRows.length} of {investments.length} total investments
          </Badge>
        </div>
      )}
    </div>
  )
}




