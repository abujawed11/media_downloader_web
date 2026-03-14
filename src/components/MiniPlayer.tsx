import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Pause, X, Maximize2 } from 'lucide-react'
import { usePlayer } from '../context/PlayerContext'

export default function MiniPlayer() {
  const navigate = useNavigate()
  const { mediaId, title, streamUrl, currentTime, isMini, restore, close, syncTime, syncPlaying } =
    usePlayer()

  const videoRef = useRef<HTMLVideoElement>(null)
  const currentTimeRef = useRef(currentTime)
  const [playing, setPlaying] = useState(false)
  const [visible, setVisible] = useState(false)
  const [hovering, setHovering] = useState(false)

  // Keep ref in sync so the play-start callback always sees the latest time
  useEffect(() => { currentTimeRef.current = currentTime }, [currentTime])

  // Slide-in: trigger visible a frame after isMini becomes true
  useEffect(() => {
    if (isMini) {
      const t = setTimeout(() => setVisible(true), 30)
      return () => clearTimeout(t)
    } else {
      setVisible(false)
    }
  }, [isMini])

  // When mini player becomes visible: wait for Watch.tsx to fully unmount,
  // then restore time and play. The 250ms delay covers the navigation + unmount cycle.
  useEffect(() => {
    if (!isMini) return
    const video = videoRef.current
    if (!video) return

    let cancelled = false

    const startPlayback = () => {
      if (cancelled || !videoRef.current) return
      const v = videoRef.current
      const t = currentTimeRef.current > 0 ? currentTimeRef.current : currentTime
      const doPlay = () => {
        if (cancelled) return
        if (t > 0) v.currentTime = t
        v.play().catch(() => {})
      }
      if (v.readyState >= 1) {
        doPlay()
      } else {
        v.addEventListener('loadedmetadata', doPlay, { once: true })
      }
    }

    // 250ms: enough for navigate(-1) + React unmount cycle to complete
    const timer = setTimeout(startPlayback, 250)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [isMini]) // eslint-disable-line react-hooks/exhaustive-deps

  // Sync time & playing state up to context every second
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const onTimeUpdate = () => syncTime(video.currentTime)
    const onPlay = () => { setPlaying(true); syncPlaying(true) }
    const onPause = () => { setPlaying(false); syncPlaying(false) }

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)
    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
    }
  }, [syncTime, syncPlaying])

  // Pause video when mini player hides
  useEffect(() => {
    if (!isMini) videoRef.current?.pause()
  }, [isMini])

  if (!mediaId || !streamUrl) return null

  const togglePlay = (e: React.MouseEvent) => {
    e.stopPropagation()
    const video = videoRef.current
    if (!video) return
    video.paused ? video.play() : video.pause()
  }

  const handleClose = (e: React.MouseEvent) => {
    e.stopPropagation()
    videoRef.current?.pause()
    close()
  }

  const handleRestore = () => {
    syncTime(videoRef.current?.currentTime ?? currentTime)
    restore()
    navigate(`/watch/${mediaId}`)
  }

  return (
    <div
      className={[
        'fixed bottom-4 right-4 z-50 rounded-xl overflow-hidden shadow-2xl',
        'border border-white/10 bg-black',
        'transition-transform duration-300 ease-out',
        isMini && visible ? 'translate-y-0' : 'translate-y-[calc(100%+2rem)]',
      ].join(' ')}
      style={{ width: 320 }}
    >
      {/* Video area */}
      <div
        className="relative cursor-pointer"
        style={{ width: 320, height: 180 }}
        onClick={handleRestore}
        onMouseEnter={() => setHovering(true)}
        onMouseLeave={() => setHovering(false)}
      >
        <video
          ref={videoRef}
          src={isMini ? streamUrl : undefined}
          className="w-full h-full object-cover"
          playsInline
        />

        {/* Hover overlay */}
        <div
          className={[
            'absolute inset-0 bg-black/40 flex items-center justify-center',
            'transition-opacity duration-200',
            hovering ? 'opacity-100' : 'opacity-0',
          ].join(' ')}
        >
          <button
            onClick={togglePlay}
            className="size-12 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center
                       hover:bg-white/30 transition-colors"
          >
            {playing
              ? <Pause className="size-5 text-white fill-white" />
              : <Play className="size-5 text-white fill-white ml-0.5" />
            }
          </button>
        </div>

        {/* Top-right action buttons */}
        <div className="absolute top-2 right-2 flex gap-1">
          <button
            onClick={handleRestore}
            className="size-7 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center
                       hover:bg-black/80 transition-colors"
            title="Expand"
          >
            <Maximize2 className="size-3.5 text-white" />
          </button>
          <button
            onClick={handleClose}
            className="size-7 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center
                       hover:bg-red-600 transition-colors"
            title="Close"
          >
            <X className="size-3.5 text-white" />
          </button>
        </div>
      </div>

      {/* Title bar */}
      <div
        className="px-3 py-2 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={handleRestore}
      >
        <p className="text-xs text-white/80 truncate">{title}</p>
        <p className="text-[10px] text-white/40 mt-0.5">Click to expand</p>
      </div>
    </div>
  )
}
