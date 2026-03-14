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
  getTime: () => number   // reads the ref — always returns the latest time
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

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<PlayerState>(INITIAL)
  // Use a ref for currentTime so syncTime doesn't trigger re-renders every second
  const currentTimeRef = useRef(0)

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

  return (
    <PlayerContext.Provider value={{ ...state, openPlayer, minimize, restore, close, syncTime, syncPlaying, getTime }}>
      {children}
    </PlayerContext.Provider>
  )
}

export function usePlayer() {
  const ctx = useContext(PlayerContext)
  if (!ctx) throw new Error('usePlayer must be used inside PlayerProvider')
  return ctx
}
