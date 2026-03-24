import { createContext, useContext, useRef, useState, useCallback } from 'react'
import type { ReactNode } from 'react'

interface PlayerState {
  mediaId: string | null
  title: string
  streamUrl: string
  currentTime: number
  isPlaying: boolean
  isMini: boolean
}

interface PlayerContextValue extends PlayerState {
  openPlayer: (mediaId: string, title: string, streamUrl: string) => void
  minimize: () => void
  restore: () => void
  close: () => void
  syncTime: (t: number) => void
  syncPlaying: (playing: boolean) => void
  getTime: () => number     // reads the ref — always returns the latest time
  syncVolume: (v: number) => void
  getVolume: () => number
}

const PlayerContext = createContext<PlayerContextValue | null>(null)

const INITIAL: PlayerState = {
  mediaId: null,
  title: '',
  streamUrl: '',
  currentTime: 0,
  isPlaying: false,
  isMini: false,
}

const VOLUME_KEY = 'player_volume'

function readSavedVolume(): number {
  try {
    const v = parseFloat(localStorage.getItem(VOLUME_KEY) ?? '')
    if (!isNaN(v) && v >= 0 && v <= 1) return v
  } catch { /* ignore */ }
  return 1
}

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PlayerState>(INITIAL)
  // Use a ref for currentTime so syncTime doesn't trigger re-renders every second
  const currentTimeRef = useRef(0)
  // Volume ref — persisted to localStorage, shared across Watch ↔ MiniPlayer
  const volumeRef = useRef<number>(readSavedVolume())

  const openPlayer = useCallback((mediaId: string, title: string, streamUrl: string) => {
    setState(prev => ({
      ...prev,
      mediaId,
      title,
      streamUrl,
      // If same video reopened from mini player, keep the time
      currentTime: prev.mediaId === mediaId ? currentTimeRef.current : 0,
      isMini: false,
    }))
  }, [])

  const minimize = useCallback(() => {
    setState(prev => ({ ...prev, isMini: true, currentTime: currentTimeRef.current }))
  }, [])

  const restore = useCallback(() => {
    setState(prev => ({ ...prev, isMini: false, currentTime: currentTimeRef.current }))
  }, [])

  const close = useCallback(() => {
    currentTimeRef.current = 0
    setState(INITIAL)
  }, [])

  const syncTime = useCallback((t: number) => {
    currentTimeRef.current = t
  }, [])

  const syncPlaying = useCallback((playing: boolean) => {
    setState(prev => ({ ...prev, isPlaying: playing }))
  }, [])

  const getTime = useCallback(() => currentTimeRef.current, [])

  const syncVolume = useCallback((v: number) => {
    volumeRef.current = v
    try { localStorage.setItem(VOLUME_KEY, String(v)) } catch { /* ignore */ }
  }, [])

  const getVolume = useCallback(() => volumeRef.current, [])

  return (
    <PlayerContext.Provider value={{ ...state, openPlayer, minimize, restore, close, syncTime, syncPlaying, getTime, syncVolume, getVolume }}>
      {children}
    </PlayerContext.Provider>
  )
}

export function usePlayer() {
  const ctx = useContext(PlayerContext)
  if (!ctx) throw new Error('usePlayer must be used inside PlayerProvider')
  return ctx
}
