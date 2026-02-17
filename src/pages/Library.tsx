import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, SortAsc, SortDesc, Loader2, Film, RefreshCw, CloudUpload, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import MediaCard from '../components/MediaCard'
import ContinueWatchingRow from '../components/ContinueWatchingRow'
import { useLibrarySocket } from '../hooks/useLibrarySocket'
import {
  fetchLibrary,
  fetchContinueWatching,
  fetchWatchProgress,
  fetchProcessing,
  deleteMediaItem,
  fetchLibraryStats,
} from '../lib/libraryApi'

const PLATFORMS = ['youtube', 'instagram', 'facebook', 'twitter', 'tiktok', 'other']
const SORT_OPTIONS = [
  { value: 'added_date', label: 'Date Added' },
  { value: 'title', label: 'Title' },
  { value: 'duration', label: 'Duration' },
  { value: 'view_count', label: 'Most Viewed' },
]

export default function Library() {
  const qc = useQueryClient()

  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [platform, setPlatform] = useState('')
  const [sortBy, setSortBy] = useState('added_date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(1)
  const LIMIT = 24

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['library', page, search, platform, sortBy, sortOrder],
    queryFn: () =>
      fetchLibrary({ page, limit: LIMIT, search: search || undefined, platform: platform || undefined, sort_by: sortBy, sort_order: sortOrder }),
  })

  // WebSocket for live upload progress — also triggers cache invalidation on complete/error
  const uploadProgress = useLibrarySocket()

  const { data: processingItems = [] } = useQuery({
    queryKey: ['library-processing'],
    queryFn: fetchProcessing,
    // No polling needed — WebSocket invalidates this query automatically
  })

  const { data: continueWatching = [] } = useQuery({
    queryKey: ['continue-watching'],
    queryFn: () => fetchContinueWatching(10),
  })

  // Fetch progress for each continue-watching item
  const { data: progressMap = {} } = useQuery({
    queryKey: ['continue-watching-progress', continueWatching.map(i => i.id)],
    queryFn: async () => {
      const entries = await Promise.all(
        continueWatching.map(async item => {
          try {
            const p = await fetchWatchProgress(item.id)
            return [item.id, p.progress] as [string, number]
          } catch {
            return [item.id, 0] as [string, number]
          }
        })
      )
      return Object.fromEntries(entries)
    },
    enabled: continueWatching.length > 0,
  })

  const { data: stats } = useQuery({
    queryKey: ['library-stats'],
    queryFn: fetchLibraryStats,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteMediaItem(id, true),
    onSuccess: () => {
      toast.success('Deleted from library')
      qc.invalidateQueries({ queryKey: ['library'] })
      qc.invalidateQueries({ queryKey: ['library-stats'] })
      qc.invalidateQueries({ queryKey: ['continue-watching'] })
      qc.invalidateQueries({ queryKey: ['library-processing'] })
    },
    onError: () => toast.error('Failed to delete'),
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const toggleSort = () => setSortOrder(p => p === 'desc' ? 'asc' : 'desc')

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const pages = data?.pages ?? 1

  return (
    <div className="space-y-6">

      {/* ── Filter bar (search + platform chips + sort — all in one block) ── */}
      <div className="rounded-xl bg-zinc-900 border border-white/5 p-4 space-y-3">
        {/* Row 1: search + sort */}
        <div className="flex items-center gap-2">
          <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-zinc-500 pointer-events-none" />
              <input
                value={searchInput}
                onChange={e => setSearchInput(e.target.value)}
                placeholder="Search your library..."
                className="w-full bg-zinc-800 border border-white/10 rounded-lg pl-9 pr-4 py-2 text-sm text-white
                           placeholder-zinc-500 focus:outline-none focus:border-yellow-400/50 transition-colors"
              />
            </div>
            {search && (
              <button type="button" onClick={() => { setSearch(''); setSearchInput(''); setPage(1) }}
                className="text-xs text-zinc-400 hover:text-white transition-colors px-1">
                ✕ Clear
              </button>
            )}
          </form>

          <div className="flex items-center gap-1.5 shrink-0">
            <select
              value={sortBy}
              onChange={e => { setSortBy(e.target.value); setPage(1) }}
              className="bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
            >
              {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <button onClick={toggleSort} className="btn-ghost p-2" title={sortOrder === 'desc' ? 'Newest first' : 'Oldest first'}>
              {sortOrder === 'desc' ? <SortDesc className="size-4" /> : <SortAsc className="size-4" />}
            </button>
            <button onClick={() => refetch()} className="btn-ghost p-2" title="Refresh">
              <RefreshCw className="size-4" />
            </button>
          </div>
        </div>

        {/* Row 2: platform chips */}
        <div className="flex flex-wrap gap-1.5">
          {PLATFORMS.map(p => (
            <button
              key={p}
              onClick={() => { setPlatform(prev => prev === p ? '' : p); setPage(1) }}
              className={`px-3 py-1 rounded-full text-xs font-medium capitalize border transition-all
                ${platform === p
                  ? 'bg-yellow-400 text-black border-yellow-400'
                  : 'bg-zinc-800 text-zinc-400 border-transparent hover:border-white/20 hover:text-white'}`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* ── Processing / Uploading videos ─────────────────────────────────── */}
      {processingItems.length > 0 && (
        <div className="space-y-2">
          {processingItems.map(item => {
            const percent = uploadProgress[item.id]
            const isError = item.file_status === 'error'
            return (
              <div
                key={item.id}
                className={`flex items-center gap-3 rounded-lg px-4 py-3 border text-sm
                  ${isError
                    ? 'bg-red-950/40 border-red-500/30'
                    : 'bg-zinc-900 border-yellow-400/20'}`}
              >
                {isError
                  ? <AlertCircle className="size-4 text-red-400 shrink-0" />
                  : <CloudUpload className="size-4 text-yellow-400 shrink-0 animate-pulse" />
                }
                <span className="flex-1 truncate font-medium text-white">{item.title}</span>

                {/* Progress bar — only while uploading */}
                {!isError && percent !== undefined && (
                  <div className="shrink-0 flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-zinc-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-400 rounded-full transition-all duration-300"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <span className="text-xs text-yellow-400 w-8 text-right">{percent}%</span>
                  </div>
                )}

                <span className={`shrink-0 text-xs ${isError ? 'text-red-400' : 'text-zinc-500'}`}>
                  {isError
                    ? 'Upload failed'
                    : percent !== undefined
                      ? 'Uploading…'
                      : 'Waiting…'}
                </span>

                {isError && (
                  <button
                    onClick={() => deleteMutation.mutate(item.id)}
                    className="shrink-0 text-xs text-zinc-500 hover:text-white border border-white/10 hover:border-white/30
                               px-2 py-0.5 rounded transition-colors ml-2"
                    title="Dismiss"
                  >
                    Dismiss
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* ── Continue Watching ──────────────────────────────────────────────── */}
      {continueWatching.length > 0 && (
        <ContinueWatchingRow items={continueWatching} progressMap={progressMap} />
      )}

      {/* ── Stats bar ──────────────────────────────────────────────────────── */}
      {stats && stats.total_videos > 0 && (
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span>
            <strong className="text-zinc-300">{stats.total_videos}</strong> video{stats.total_videos !== 1 ? 's' : ''}
          </span>
          {Object.entries(stats.by_platform).map(([p, count]) => (
            <span key={p} className="capitalize">{p}: <strong className="text-zinc-300">{count}</strong></span>
          ))}
        </div>
      )}

      {/* ── Grid ──────────────────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="size-8 animate-spin text-yellow-400" />
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3 text-zinc-400">
          <p>Failed to load library. Is PostgreSQL running?</p>
          <button onClick={() => refetch()} className="btn-ghost text-sm">Try again</button>
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4 text-zinc-400">
          <Film className="size-16 text-zinc-700" />
          <p className="text-lg">
            {search || platform ? 'No results found.' : 'Your library is empty.'}
          </p>
          {!search && !platform && (
            <p className="text-sm text-zinc-500">Download a video from the Home page to get started.</p>
          )}
        </div>
      ) : (
        <>
          <p className="text-xs text-zinc-500">
            {total} video{total !== 1 ? 's' : ''}
            {search && ` matching "${search}"`}
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {items.map(item => (
              <MediaCard
                key={item.id}
                item={item}
                onDelete={id => deleteMutation.mutate(id)}
              />
            ))}
          </div>

          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
                className="btn-ghost px-4 py-2 text-sm disabled:opacity-40">Previous</button>
              <span className="text-sm text-zinc-400">Page {page} of {pages}</span>
              <button disabled={page >= pages} onClick={() => setPage(p => p + 1)}
                className="btn-ghost px-4 py-2 text-sm disabled:opacity-40">Next</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
