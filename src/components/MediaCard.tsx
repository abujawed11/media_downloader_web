import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Eye, Trash2 } from 'lucide-react'
import type { MediaItem } from '../lib/libraryApi'
import { formatDuration, formatFileSize, platformLabel, platformColor } from '../lib/libraryApi'
import { BASE_URL } from '../lib/config'

interface Props {
  item: MediaItem
  watchProgress?: number  // 0-100
  onDelete?: (id: string) => void
}

/** Resolve relative /media-storage/... URLs against the API server origin */
function resolveThumbnail(url?: string): string {
  if (!url) return ''
  if (url.startsWith('/')) return `${BASE_URL}${url}`
  return url
}

export default function MediaCard({ item, watchProgress, onDelete }: Props) {
  const navigate = useNavigate()
  const [imgError, setImgError] = useState(false)

  const thumbnailSrc = !imgError ? resolveThumbnail(item.thumbnail_url) : ''

  return (
    <div
      className="group relative flex flex-col rounded-lg overflow-hidden bg-zinc-900 border border-white/5 cursor-pointer
                 hover:border-white/20 hover:scale-[1.02] transition-all duration-200 shadow-lg"
      onClick={() => navigate(`/watch/${item.id}`)}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-zinc-800 overflow-hidden">
        {thumbnailSrc ? (
          <img
            src={thumbnailSrc}
            alt={item.title}
            className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-zinc-800">
            <Play className="size-10 text-zinc-600" />
          </div>
        )}

        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="size-12 rounded-full bg-white/90 flex items-center justify-center">
            <Play className="size-5 text-black fill-black ml-0.5" />
          </div>
        </div>

        {/* Duration badge */}
        {item.duration && (
          <span className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded font-mono">
            {formatDuration(item.duration)}
          </span>
        )}

        {/* Watch progress bar */}
        {watchProgress !== undefined && watchProgress > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
            <div
              className="h-full bg-red-500 transition-all"
              style={{ width: `${Math.min(watchProgress, 100)}%` }}
            />
          </div>
        )}

        {/* Platform badge */}
        {item.source_platform && (
          <span className={`absolute top-2 left-2 text-white text-[10px] px-1.5 py-0.5 rounded font-medium ${platformColor(item.source_platform)}`}>
            {platformLabel(item.source_platform)}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col flex-1 p-3 gap-1">
        <h3 className="text-sm font-medium text-white line-clamp-2 leading-snug" title={item.title}>
          {item.title}
        </h3>

        <div className="flex items-center gap-2 mt-auto pt-2 text-xs text-zinc-400 flex-wrap">
          {item.resolution && (
            <span className="bg-zinc-700 text-zinc-300 px-1.5 py-0.5 rounded text-[10px] font-mono">
              {item.resolution}
            </span>
          )}
          {item.file_size && <span>{formatFileSize(item.file_size)}</span>}
          {item.view_count > 0 && (
            <span className="flex items-center gap-1 ml-auto">
              <Eye className="size-3" />
              {item.view_count}
            </span>
          )}
        </div>

        {item.uploader && (
          <p className="text-xs text-zinc-500 truncate">{item.uploader}</p>
        )}
      </div>

      {/* Delete on hover */}
      {onDelete && (
        <button
          className="absolute top-2 right-2 size-6 rounded-full bg-black/70 flex items-center justify-center
                     opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 z-10"
          onClick={e => { e.stopPropagation(); onDelete(item.id) }}
          title="Delete"
        >
          <Trash2 className="size-3 text-white" />
        </button>
      )}
    </div>
  )
}
