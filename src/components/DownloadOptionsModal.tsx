import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useModal } from '../hooks/useModal'
import { mediaApi } from '../lib/mediaApi'
import type { InfoResponse, FormatItem } from '../features/downloads/types'
import { detectPlatformFromUrl } from '../utils/platform'
import { useDownloads } from '../features/downloads/downloads.slice'
import { BASE_URL } from '../lib/config'

export default function DownloadOptionsModal() {
  const { subscribe } = useModal()
  const navigate = useNavigate()
  const upsertJob = useDownloads(s => s.upsertJob)

  const [open, setOpen] = useState(false)
  const [payload, setPayload] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [info, setInfo] = useState<InfoResponse | null>(null)

  useEffect(() => {
    return subscribe(async (name, payload) => {
      if (name === 'downloadOptions') {
        setPayload(payload)
        setInfo(null)
        setOpen(true)
        setLoading(true)
        try {
          const url = String(payload?.url || '')
          const data = await mediaApi.info(url)
          setInfo(data)
        } catch (e) {
          console.error(e)
        } finally {
          setLoading(false)
        }
      } else {
        setOpen(false)
        setPayload(null)
        setInfo(null)
      }
    })
  }, [subscribe])

  if (!open) return null

  const url = String(payload?.url || '')
  const platform = detectPlatformFromUrl(url)

  function startDownload(fmt: FormatItem) {
    ;(async () => {
      try {
        const job = await mediaApi.startJob({
          url,
          format_string: fmt.format_string,
          title: info?.title,
          ext: fmt.ext,
        })
        upsertJob({ ...job, label: fmt.label, platform })
        setOpen(false)
        navigate('/uploads')  // take user to progress page immediately
      } catch (e) {
        console.error(e)
        setOpen(false)
      }
    })()
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
      <div className="card w-full max-w-lg max-h-[90vh] flex flex-col p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-lg font-semibold">Save to Library</div>
          <button className="btn-ghost" onClick={() => setOpen(false)}>Close</button>
        </div>

        <div className="text-sm text-white/60 mb-3">{platform} • {url}</div>

        {loading && <div className="text-white/80">Loading video info…</div>}

        {!loading && info && (
          <div className="grid gap-3 overflow-y-auto min-h-0">
            {info.thumbnail && (
              <img
                src={`${BASE_URL}/proxy-image?url=${encodeURIComponent(info.thumbnail)}`}
                alt={info.title}
                className="w-full rounded-xl aspect-video object-cover mb-2"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                }}
              />
            )}

            <div className="font-medium">{info.title}</div>

            <div className="grid gap-2">
              {info.formats.map(f => (
                <button
                  key={f.format_string}
                  onClick={() => startDownload(f)}
                  className="btn-primary justify-between"
                >
                  <div className="flex flex-col items-start">
                    <span>{f.label}</span>
                    {f.filesize && <span className="text-xs opacity-70">{f.filesize}</span>}
                  </div>
                  <span className="text-sm opacity-80">{f.ext?.toUpperCase()}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {!loading && !info && (
          <div className="text-white/70">No info available.</div>
        )}
      </div>
    </div>
  )
}
