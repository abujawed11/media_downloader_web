import { useState } from 'react'
import { useModal } from '../hooks/useModal'
import { detectPlatformFromUrl } from '../utils/platform'

export default function Home() {
  const [url, setUrl] = useState('')
  const { open } = useModal()

  function handleGetInfo() {
    if (!url) return
    const platform = detectPlatformFromUrl(url)
    open('downloadOptions', { url, platform })
  }

  return (
    <div className="card p-6">
      <h2 className="text-2xl font-semibold mb-3">Paste a URL</h2>
      <p className="text-white/70 mb-4">Supports YouTube, Instagram, Facebook, Twitter (X)…</p>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://example.com/video"
          className="w-full rounded-2xl bg-white/5 border-white/10 text-white placeholder-white/40 focus:border-yellow-400 focus:ring-yellow-400"
        />
        <button type="button" className="btn-primary" onClick={handleGetInfo}>Get Info</button>
      </div>
    </div>
  )
}
