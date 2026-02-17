import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, ExternalLink, Download, Calendar, User, Tag,
  Clock, Eye, Film, Loader2
} from 'lucide-react'
import {
  fetchMediaItem,
  fetchWatchProgress,
  updateWatchProgress,
  formatDuration,
  formatFileSize,
  platformLabel,
} from '../lib/libraryApi'
import { BASE_URL } from '../lib/config'

function resolveThumbnail(url?: string) {
  if (!url) return undefined
  if (url.startsWith('/')) return `${BASE_URL}${url}`
  if (url.startsWith(BASE_URL)) return url
  return `${BASE_URL}/proxy-image?url=${encodeURIComponent(url)}`
}

const PROGRESS_SAVE_INTERVAL_MS = 5_000  // Save progress every 5 seconds

export default function Watch() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const videoRef = useRef<HTMLVideoElement>(null)
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const [videoError, setVideoError] = useState<string | null>(null)

  const { data: media, isLoading, isError } = useQuery({
    queryKey: ['media', id],
    queryFn: () => fetchMediaItem(id!),
    enabled: !!id,
  })

  const { data: savedProgress } = useQuery({
    queryKey: ['progress', id],
    queryFn: () => fetchWatchProgress(id!),
    enabled: !!id,
  })

  // Restore saved position once video metadata is loaded
  useEffect(() => {
    const video = videoRef.current
    if (!video || !savedProgress || savedProgress.current_time <= 0) return

    const onLoaded = () => {
      // Don't restore if almost finished (>95%)
      if (savedProgress.progress < 95 && savedProgress.current_time > 3) {
        video.currentTime = savedProgress.current_time
      }
    }
    video.addEventListener('loadedmetadata', onLoaded)
    return () => video.removeEventListener('loadedmetadata', onLoaded)
  }, [savedProgress, media])

  // Periodically save watch progress
  const saveProgress = useCallback(() => {
    const video = videoRef.current
    if (!video || !id || video.paused || !video.duration) return
    updateWatchProgress(id, Math.floor(video.currentTime), Math.floor(video.duration)).catch(() => {})
  }, [id])

  useEffect(() => {
    progressTimerRef.current = setInterval(saveProgress, PROGRESS_SAVE_INTERVAL_MS)
    return () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
      // Save one last time on unmount
      saveProgress()
    }
  }, [saveProgress])

  // Build the streaming and download URLs
  const streamUrl   = id ? `${BASE_URL}/api/library/${id}/stream` : ''
  const downloadUrl = id ? `${BASE_URL}/api/library/${id}/download` : ''

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="size-10 animate-spin text-yellow-400" />
      </div>
    )
  }

  if (isError || !media) {
    return (
      <div className="flex flex-col items-center justify-center py-32 gap-4 text-zinc-400">
        <Film className="size-16 text-zinc-700" />
        <p>Video not found or unavailable.</p>
        <button onClick={() => navigate('/library')} className="btn-ghost">
          Back to Library
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
      >
        <ArrowLeft className="size-4" />
        Back
      </button>

      {/* ── Video player ─────────────────────────────────────────────────── */}
      <div className="relative rounded-xl overflow-hidden bg-black shadow-2xl aspect-video">
        {videoError ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-zinc-400">
            <Film className="size-12 text-zinc-600" />
            <p className="text-sm">{videoError}</p>
            <a href={streamUrl} target="_blank" rel="noopener noreferrer" className="btn-ghost text-sm">
              Try Direct Link
            </a>
          </div>
        ) : (
          <video
            ref={videoRef}
            src={streamUrl}
            controls
            className="w-full h-full"
            onError={() => setVideoError('Failed to load video. The file may have been removed.')}
            poster={resolveThumbnail(media.thumbnail_url)}
            preload="metadata"
          />
        )}
      </div>

      {/* ── Metadata ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: title + description */}
        <div className="lg:col-span-2 space-y-4">
          <div>
            <h1 className="text-xl font-semibold text-white leading-snug">{media.title}</h1>
            <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-zinc-400">
              {media.uploader && (
                <span className="flex items-center gap-1.5">
                  <User className="size-3.5" />
                  {media.uploader}
                </span>
              )}
              {media.duration && (
                <span className="flex items-center gap-1.5">
                  <Clock className="size-3.5" />
                  {formatDuration(media.duration)}
                </span>
              )}
              {media.view_count > 0 && (
                <span className="flex items-center gap-1.5">
                  <Eye className="size-3.5" />
                  {media.view_count} view{media.view_count !== 1 ? 's' : ''}
                </span>
              )}
              {media.upload_date && (
                <span className="flex items-center gap-1.5">
                  <Calendar className="size-3.5" />
                  {new Date(media.upload_date).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>

          {media.description && (
            <div className="bg-zinc-900 rounded-lg p-4 text-sm text-zinc-300 whitespace-pre-line max-h-48 overflow-y-auto">
              {media.description}
            </div>
          )}

          {/* Tags */}
          {media.tags && media.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {media.tags.slice(0, 20).map(tag => (
                <span
                  key={tag}
                  className="flex items-center gap-1 bg-zinc-800 text-zinc-300 text-xs px-2 py-0.5 rounded-full"
                >
                  <Tag className="size-2.5" />
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Right: file info + actions */}
        <div className="space-y-4">
          <div className="bg-zinc-900 rounded-lg p-4 space-y-3 text-sm">
            <h3 className="font-semibold text-white text-base mb-2">File Info</h3>
            <InfoRow label="Platform" value={platformLabel(media.source_platform)} />
            {media.resolution && <InfoRow label="Resolution" value={media.resolution} />}
            {media.format && <InfoRow label="Format" value={media.format.toUpperCase()} />}
            {media.file_size && <InfoRow label="Size" value={formatFileSize(media.file_size)} />}
            {media.added_date && (
              <InfoRow
                label="Added"
                value={new Date(media.added_date).toLocaleDateString()}
              />
            )}
          </div>

          {/* Actions */}
          <div className="space-y-2">
            <a
              href={media.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost w-full flex items-center justify-center gap-2 text-sm py-2"
            >
              <ExternalLink className="size-4" />
              View Source
            </a>
            <a
              href={downloadUrl}
              download
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost w-full flex items-center justify-center gap-2 text-sm py-2"
            >
              <Download className="size-4" />
              Download File
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-200 text-right truncate max-w-[60%]">{value}</span>
    </div>
  )
}
