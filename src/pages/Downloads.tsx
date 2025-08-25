import { useEffect, useMemo, useState } from 'react'
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

  // Poll active jobs
  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const active = jobs.filter(j => !['done','error','canceled'].includes(j.status))
        if (active.length === 0) return
        await Promise.all(active.map(async j => {
          const fresh = await mediaApi.getJob(j.id)
          upsert(fresh)
        }))
      } catch (e) { /* ignore transient */ }
    }, 1000)
    return () => clearInterval(timer)
  }, [jobs, upsert])

  return (
    <div className="grid gap-4">
      <h2 className="text-2xl font-semibold">Downloads</h2>
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
  const pct = Math.round((job.progress || 0) * 100)

  async function pause()  { upsert(await mediaApi.pauseJob(job.id)) }
  async function resume() { upsert(await mediaApi.resumeJob(job.id)) }
  async function cancel() { upsert(await mediaApi.cancelJob(job.id)) }

  const fileHref = useMemo(() => mediaApi.fileUrl(job.id), [job.id])

  const canPause   = job.status === 'downloading'
  const canResume  = job.status === 'paused' || job.status === 'error'
  const canCancel  = ['queued','downloading','paused','merging'].includes(job.status)
  const canOpen    = job.status === 'done'

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
          {canOpen && (
            <a className="btn-primary" href={fileHref} target="_blank" rel="noreferrer">
              Open
            </a>
          )}
        </div>
      </div>

      <div className="mt-3 h-2 rounded-full bg-white/10 overflow-hidden">
        <div className="h-full bg-yellow-400" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
