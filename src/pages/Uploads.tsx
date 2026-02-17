import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, CloudUpload, Loader2, XCircle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { mediaApi } from '../lib/mediaApi'
import { useDownloads } from '../features/downloads/downloads.slice'
import type { DownloadJobDTO } from '../features/downloads/types'
import { bytesHuman, speedHuman, etaHuman } from '../utils/format'
import { useLibrarySocket } from '../hooks/useLibrarySocket'
import { fetchProcessing } from '../lib/libraryApi'

export default function Uploads() {
  const jobs    = useDownloads(s => s.jobs)
  const setJobs = useDownloads(s => s.setJobs)
  const upsert  = useDownloads(s => s.upsertJob)

  const { jobProgress, completedJobIds } = useLibrarySocket()

  // Poll processing items as fallback for missed WebSocket events.
  // When a job moves from 'processing' → 'available' in the DB, it disappears
  // from this list — that's our signal that phase 2 is done.
  const { data: processingItems = [] } = useQuery({
    queryKey: ['library-processing'],
    queryFn: fetchProcessing,
    refetchInterval: 8_000,
    enabled: jobs.some(j => j.status === 'done'),
  })
  // Build a set of titles currently still processing — used as fallback below
  const processingTitles = new Set(processingItems.map(i => i.title))

  // Load existing jobs from server on mount
  useEffect(() => {
    ;(async () => {
      try { setJobs(await mediaApi.listJobs()) } catch { /* ignore */ }
    })()
  }, [setJobs])

  // Poll active jobs every second
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const jobsToUpdate = jobs.filter(j => {
          if (!['done', 'error', 'canceled'].includes(j.status)) return true
          if (j.status === 'done') {
            const cutoff = (j.completedAt ?? 0) + 5000
            return Date.now() < cutoff
          }
          return false
        })
        if (jobsToUpdate.length === 0) return
        await Promise.all(jobsToUpdate.map(async j => upsert(await mediaApi.getJob(j.id))))
      } catch { /* ignore transient */ }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobs, upsert])

  const clearHistory = async () => {
    const done = jobs.filter(j => j.status === 'done' || j.status === 'error')
    if (done.length === 0) return
    if (!window.confirm(`Clear ${done.length} completed/failed upload${done.length > 1 ? 's' : ''} from history?\n\n(Videos remain in your Library)`)) return
    try {
      await mediaApi.clearAllJobs(false)
      const removeJob = useDownloads.getState().removeJob
      done.forEach(j => removeJob(j.id))
    } catch { alert('Failed to clear history') }
  }

  const hasCompleted = jobs.some(j => j.status === 'done' || j.status === 'error')

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Uploads</h2>
        {hasCompleted && (
          <button onClick={clearHistory} className="btn-ghost text-sm">
            🗑️ Clear History
          </button>
        )}
      </div>

      {jobs.length === 0 ? (
        <p className="text-white/60">No uploads yet. Paste a URL on the Upload page to get started.</p>
      ) : (
        jobs.map(j => {
          // isCloudSaved = WebSocket fired 'complete' OR job is 'done' and title
          // is no longer in the processing list (polling fallback)
          const savedViaWS     = completedJobIds[j.id] === true
          const savedViaPoll   = j.status === 'done' && !processingTitles.has(j.title ?? '')
          return (
          <JobRow
            key={j.id}
            job={j}
            phase2Percent={jobProgress[j.id]}
            isCloudSaved={savedViaWS || savedViaPoll}
          />
          )
        })
      )}
    </div>
  )
}

// ─── Status helpers ───────────────────────────────────────────────────────── //

function phase1Label(status: DownloadJobDTO['status']): string {
  switch (status) {
    case 'queued':      return 'Waiting in queue…'
    case 'downloading': return 'Fetching video…'
    case 'paused':      return 'Paused'
    case 'merging':     return 'Processing…'
    case 'done':        return 'Fetched'
    case 'error':       return 'Failed'
    case 'canceled':    return 'Canceled'
    default:            return status
  }
}

// ─── Job row ─────────────────────────────────────────────────────────────── //

interface JobRowProps {
  job: DownloadJobDTO
  phase2Percent: number | undefined   // cloud upload % (from WebSocket)
  isCloudSaved: boolean               // cloud upload finished
}

function JobRow({ job, phase2Percent, isCloudSaved }: JobRowProps) {
  const upsert    = useDownloads(s => s.upsertJob)
  const removeJob = useDownloads(s => s.removeJob)

  const pct = Math.round((job.progress || 0) * 100)

  const isPhase1Active  = !['done', 'error', 'canceled'].includes(job.status)
  const isPhase1Done    = job.status === 'done' || job.status === 'error' || job.status === 'canceled'
  const isFailed        = job.status === 'error'
  const isCanceled      = job.status === 'canceled'
  const isPhase2Active  = job.status === 'done' && !isCloudSaved && phase2Percent !== undefined
  const isPhase2Waiting = job.status === 'done' && !isCloudSaved && phase2Percent === undefined

  async function pause()  { upsert(await mediaApi.pauseJob(job.id))  }
  async function resume() { upsert(await mediaApi.resumeJob(job.id)) }
  async function cancel() { upsert(await mediaApi.cancelJob(job.id)) }
  async function remove() {
    try { await mediaApi.deleteJob(job.id, false); removeJob(job.id) }
    catch { console.error('Failed to remove job') }
  }

  const canPause  = job.status === 'downloading'
  const canResume = job.status === 'paused' || job.status === 'error'
  const canCancel = ['queued', 'downloading', 'paused', 'merging'].includes(job.status)
  const canRemove = ['done', 'error', 'canceled'].includes(job.status)

  return (
    <div className="card p-4 space-y-3">

      {/* ── Header row: title + action buttons ── */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="font-medium truncate">{job.title || job.url}</div>
          {job.platform && (
            <div className="text-xs text-white/40 capitalize mt-0.5">{job.platform}</div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {canPause  && <button className="btn-ghost text-sm" onClick={pause}>Pause</button>}
          {canResume && <button className="btn-primary text-sm" onClick={resume}>Resume</button>}
          {canCancel && <button className="btn-ghost text-sm" onClick={cancel}>Cancel</button>}
          {canRemove && (
            <button className="btn-ghost text-white/40 hover:text-white/80 text-sm" onClick={remove} title="Remove from history">
              ✕
            </button>
          )}
        </div>
      </div>

      {/* ── Fully done: saved to library ── */}
      {isCloudSaved && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <CheckCircle2 className="size-4" />
            <span>Saved to your library</span>
          </div>
          <Link to="/library" className="btn-primary text-sm px-4 py-1.5">
            View in Library →
          </Link>
        </div>
      )}

      {/* ── Failed ── */}
      {isFailed && !canResume && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <XCircle className="size-4" />
          <span>{job.error || 'Upload failed'}</span>
        </div>
      )}

      {/* ── Canceled ── */}
      {isCanceled && (
        <div className="text-sm text-white/40">Canceled</div>
      )}

      {/* ── Phase 1: Fetching video (active) ── */}
      {isPhase1Active && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-yellow-400 font-medium">
              <Loader2 className="size-3 animate-spin" />
              {phase1Label(job.status)}
            </span>
            <span className="text-white/50">
              {bytesHuman(job.downloaded_bytes)}
              {job.total_bytes ? ` / ${bytesHuman(job.total_bytes)}` : ''}
              {job.speed_bps ? ` • ${speedHuman(job.speed_bps)}` : ''}
              {job.eta_seconds != null ? ` • ${etaHuman(job.eta_seconds)} left` : ''}
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full bg-yellow-400 rounded-full transition-all duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* ── Phase 1 done label (only shown while phase 2 is visible) ── */}
      {isPhase1Done && !isFailed && !isCanceled && !isCloudSaved && (
        <div className="flex items-center gap-1.5 text-xs text-white/50">
          <CheckCircle2 className="size-3 text-green-500" />
          Fetched{job.total_bytes ? ` (${bytesHuman(job.total_bytes)})` : ''}
        </div>
      )}

      {/* ── Phase 2: Saving to cloud ── */}
      {(isPhase2Active || isPhase2Waiting) && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-sky-400 font-medium">
              <CloudUpload className="size-3 animate-pulse" />
              Saving to cloud…
            </span>
            {isPhase2Active && (
              <span className="text-sky-400">{phase2Percent}%</span>
            )}
          </div>
          {isPhase2Active ? (
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className="h-full bg-sky-400 rounded-full transition-all duration-500"
                style={{ width: `${phase2Percent}%` }}
              />
            </div>
          ) : (
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div className="h-full w-1/3 bg-sky-400/40 rounded-full animate-pulse" />
            </div>
          )}
        </div>
      )}

      {/* ── View in Library for older 'done' jobs (no WebSocket tracking) ── */}
      {job.status === 'done' && !isCloudSaved && !isPhase2Active && !isPhase2Waiting && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white/50 text-sm">
            <CheckCircle2 className="size-4 text-green-500" />
            <span>Saved to your library</span>
          </div>
          <Link to="/library" className="btn-primary text-sm px-4 py-1.5">
            View in Library →
          </Link>
        </div>
      )}
    </div>
  )
}
