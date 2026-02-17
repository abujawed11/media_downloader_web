import { useState } from 'react'
import { CloudUpload } from 'lucide-react'
import { useModal } from '../hooks/useModal'
import { detectPlatformFromUrl } from '../utils/platform'

export default function Home() {
  const [url, setUrl] = useState('')
  const { open } = useModal()

  function handleSave() {
    if (!url.trim()) return
    const platform = detectPlatformFromUrl(url)
    open('downloadOptions', { url, platform })
  }

  return (
    <div className="card p-8 flex flex-col items-center gap-6 text-center">
      <div className="size-14 rounded-full bg-yellow-400/10 border border-yellow-400/20 flex items-center justify-center">
        <CloudUpload className="size-7 text-yellow-400" />
      </div>

      <div>
        <h2 className="text-2xl font-semibold mb-2">Save a video to your cloud</h2>
        <p className="text-white/50 text-sm">
          Paste any YouTube, Instagram, Facebook, or Twitter URL and we'll save it to your personal library.
        </p>
      </div>

      <div className="w-full max-w-xl flex flex-col sm:flex-row gap-3">
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSave()}
          placeholder="https://youtube.com/watch?v=..."
          className="flex-1 rounded-2xl bg-white/5 border border-white/10 text-white placeholder-white/30
                     px-4 py-3 focus:outline-none focus:border-yellow-400/60 transition-colors"
        />
        <button
          type="button"
          className="btn-primary px-6 py-3 rounded-2xl flex items-center gap-2 shrink-0"
          onClick={handleSave}
        >
          <CloudUpload className="size-4" />
          Save to Cloud
        </button>
      </div>

      <p className="text-xs text-white/25">
        YouTube · Instagram · Facebook · Twitter (X) · TikTok · and more
      </p>
    </div>
  )
}
