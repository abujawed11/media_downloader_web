import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { mediaApi } from '../lib/mediaApi'
import { useDownloads } from '../features/downloads/downloads.slice'
import type { DownloadJobDTO } from '../features/downloads/types'
import { bytesHuman, speedHuman, etaHuman } from '../utils/format'

export default function Downloads() {
  const jobs = useDownloads(s => s.jobs)
  const setJobs = useDownloads(s => s.setJobs)
  const upsert = useDownloads(s => s.upsertJob)

  // On mount, load existing jobs from server
  useEffect(() => {
    (async () => {
      try { setJobs(await mediaApi.listJobs()) } catch (e) { console.error(e) }
    })()
  }, [setJobs])

  // Poll active jobs and recently completed ones
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        // Poll active jobs + jobs that completed in the last 5 seconds (to get final size)
        // const now = Date.now()
        // const jobsToUpdate = jobs.filter(j => {
        //   if (!['done','error','canceled'].includes(j.status)) return true
        //   // For completed jobs, check if they finished recently (no completion timestamp available, so poll for first 5 updates after completion)
        //   if (j.status === 'done') {
        //     const updatedRecently = !j._lastPolled || (now - j._lastPolled) < 5000
        //     return updatedRecently
        //   }
        //   return false
        // })

        const jobsToUpdate = jobs.filter(j => {
          if (!['done', 'error', 'canceled'].includes(j.status)) return true;
          if (j.status === 'done') {
            // poll only for 5s after first completion
            const cutoff = (j.completedAt ?? 0) + 5000;
            return Date.now() < cutoff;
          }
          return false;
        });

        if (jobsToUpdate.length === 0) return
        await Promise.all(jobsToUpdate.map(async j => {
          const fresh = await mediaApi.getJob(j.id)
          // fresh._lastPolled = now
          upsert(fresh)
        }))
      } catch (e) { /* ignore transient */ }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobs, upsert])

  // Clear all completed/error jobs
  const clearAllHistory = async () => {
    const completedJobs = jobs.filter(j => j.status === 'done' || j.status === 'error')
    if (completedJobs.length === 0) return

    const confirmed = window.confirm(
      `Clear ${completedJobs.length} completed/error downloads from history?\n\n(Videos remain in your Library)`
    )
    if (!confirmed) return

    try {
      await mediaApi.clearAllJobs(false)
      // Remove all completed/error jobs from UI
      const removeJob = useDownloads.getState().removeJob
      completedJobs.forEach(j => removeJob(j.id))
    } catch (e) {
      console.error('Failed to clear history:', e)
      alert('Failed to clear history')
    }
  }

  const hasCompletedJobs = jobs.some(j => j.status === 'done' || j.status === 'error')

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Downloads</h2>
        {hasCompletedJobs && (
          <button
            onClick={clearAllHistory}
            className="btn-ghost text-sm"
            title="Clear all completed/error downloads from history"
          >
            🗑️ Clear History
          </button>
        )}
      </div>
      {jobs.length === 0 ? (
        <p className="text-white/60">No downloads yet.</p>
      ) : (
        jobs.map(j => <JobRow key={j.id} job={j} />)
      )}
    </div>
  )
}

function JobRow({ job }: { job: DownloadJobDTO }) {
  const upsert = useDownloads(s => s.upsertJob)
  const removeJob = useDownloads(s => s.removeJob)
  const pct = Math.round((job.progress || 0) * 100)

  async function pause() { upsert(await mediaApi.pauseJob(job.id)) }
  async function resume() { upsert(await mediaApi.resumeJob(job.id)) }
  async function cancel() { upsert(await mediaApi.cancelJob(job.id)) }

  async function remove() {
    try {
      await mediaApi.deleteJob(job.id, false) // Don't delete file
      removeJob(job.id) // Remove from UI
    } catch (e) {
      console.error('Failed to remove job:', e)
    }
  }

  const canPause  = job.status === 'downloading'
  const canResume = job.status === 'paused' || job.status === 'error'
  const canCancel = ['queued', 'downloading', 'paused', 'merging'].includes(job.status)
  const isDone    = job.status === 'done'
  const canRemove = isDone || job.status === 'error' || job.status === 'canceled'

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="font-medium truncate">{job.title || job.url}</div>
          <div className="text-xs text-white/60">
            {job.status.toUpperCase()} • {bytesHuman(job.downloaded_bytes)}
            {job.total_bytes ? ` / ${bytesHuman(job.total_bytes)}` : ''} •
            {' '}{speedHuman(job.speed_bps)}{job.eta_seconds != null ? ` • ${etaHuman(job.eta_seconds)} left` : ''}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {canPause && <button className="btn-ghost" onClick={pause}>Pause</button>}
          {canResume && <button className="btn-primary" onClick={resume}>Resume</button>}
          {canCancel && <button className="btn-ghost" onClick={cancel}>Cancel</button>}
          {isDone && (
            <Link to="/library" className="btn-primary text-sm px-4 py-1.5">
              View in Library
            </Link>
          )}
          {canRemove && (
            <button
              className="btn-ghost text-white/40 hover:text-white/80"
              onClick={remove}
              title="Remove from history"
            >
              ❌
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-yellow-400" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
