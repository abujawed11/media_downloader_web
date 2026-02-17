import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play } from 'lucide-react'
import type { MediaItem } from '../lib/libraryApi'
import { formatDuration, platformColor, platformLabel } from '../lib/libraryApi'
import { BASE_URL } from '../lib/config'

interface Props {
  items: MediaItem[]
  progressMap?: Record<string, number>  // media_id → progress %
}

function resolveThumbnail(url?: string) {
  if (!url) return ''
  if (url.startsWith('/')) return `${BASE_URL}${url}`
  return url
}

export default function ContinueWatchingRow({ items, progressMap = {} }: Props) {
  const navigate = useNavigate()

  if (!items.length) return null

  return (
    <section>
      <h2 className="text-base font-semibold mb-3 text-white tracking-wide uppercase text-xs text-zinc-400">
        Continue Watching
      </h2>
      <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-hide">
        {items.map(item => (
          <ContinueCard
            key={item.id}
            item={item}
            progress={progressMap[item.id] ?? 0}
            onClick={() => navigate(`/watch/${item.id}`)}
          />
        ))}
      </div>
    </section>
  )
}

function ContinueCard({
  item,
  progress,
  onClick,
}: {
  item: MediaItem
  progress: number
  onClick: () => void
}) {
  const [imgError, setImgError] = useState(false)
  const thumbnailSrc = !imgError ? resolveThumbnail(item.thumbnail_url) : ''
  const pct = Math.min(Math.max(progress, 0), 100)

  return (
    <div
      onClick={onClick}
      className="group relative flex-shrink-0 w-52 cursor-pointer rounded-lg overflow-hidden
                 bg-zinc-900 border border-white/5 hover:border-white/20 hover:scale-[1.02]
                 transition-all duration-200 shadow-md"
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-zinc-800 overflow-hidden">
        {thumbnailSrc ? (
          <img
            src={thumbnailSrc}
            alt={item.title}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Play className="size-8 text-zinc-600" />
          </div>
        )}

        {/* Dark overlay + play icon on hover */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="size-10 rounded-full bg-white/90 flex items-center justify-center">
            <Play className="size-4 text-black fill-black ml-0.5" />
          </div>
        </div>

        {/* Duration */}
        {item.duration && (
          <span className="absolute bottom-6 right-2 bg-black/80 text-white text-[10px] px-1 py-0.5 rounded font-mono">
            {formatDuration(item.duration)}
          </span>
        )}

        {/* Progress bar */}
        <div className="absolute bottom-0 left-0 right-0 h-1.5 bg-white/20">
          <div
            className="h-full bg-red-500 transition-all rounded-r-full"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Info */}
      <div className="p-2.5">
        <p className="text-xs font-medium text-white line-clamp-2 leading-snug mb-1">{item.title}</p>
        <div className="flex items-center justify-between">
          {item.source_platform && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded text-white font-medium ${platformColor(item.source_platform)}`}>
              {platformLabel(item.source_platform)}
            </span>
          )}
          <span className="text-[10px] text-zinc-500 ml-auto">
            {pct.toFixed(0)}% watched
          </span>
        </div>
      </div>
    </div>
  )
}
