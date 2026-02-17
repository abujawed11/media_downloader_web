import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { BASE_URL } from '../lib/config'

type WSMessage =
  | { type: 'started';  media_id: string; job_id?: string }
  | { type: 'progress'; media_id: string; percent: number; job_id?: string }
  | { type: 'complete'; media_id: string; job_id?: string }
  | { type: 'error';    media_id: string; job_id?: string }

export interface LibrarySocketState {
  /** media_id → upload percent  (used by Library page banner) */
  progressMap: Record<string, number>
  /** job_id → upload percent  (used by Uploads page phase-2 bar) */
  jobProgress: Record<string, number>
  /** job_ids that have finished the cloud upload phase */
  completedJobIds: Record<string, true>
}

function wsUrl(): string {
  return BASE_URL.replace(/^http/, 'ws') + '/ws/library'
}

function clearHandlers(ws: WebSocket) {
  ws.onopen    = null
  ws.onmessage = null
  ws.onerror   = null
  ws.onclose   = null
}

export function useLibrarySocket(): LibrarySocketState {
  const qc = useQueryClient()
  const [state, setState] = useState<LibrarySocketState>({
    progressMap: {},
    jobProgress: {},
    completedJobIds: {},
  })
  const wsRef           = useRef<WebSocket | null>(null)
  const reconnectTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef      = useRef(true)
  // Tracks reconnect delay for simple exponential back-off
  const retryDelay      = useRef(2000)

  useEffect(() => {
    mountedRef.current = true
    retryDelay.current = 2000

    function connect() {
      if (!mountedRef.current) return

      const ws = new WebSocket(wsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        retryDelay.current = 2000 // reset back-off on successful connection
      }

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return
        try {
          const msg: WSMessage = JSON.parse(event.data as string)

          if (msg.type === 'started') {
            qc.invalidateQueries({ queryKey: ['library-processing'] })

          } else if (msg.type === 'progress') {
            setState(prev => ({
              ...prev,
              progressMap: { ...prev.progressMap, [msg.media_id]: msg.percent },
              jobProgress: msg.job_id
                ? { ...prev.jobProgress, [msg.job_id]: msg.percent }
                : prev.jobProgress,
            }))

          } else if (msg.type === 'complete') {
            setState(prev => {
              const progressMap = { ...prev.progressMap }
              delete progressMap[msg.media_id]
              const jobProgress = { ...prev.jobProgress }
              if (msg.job_id) delete jobProgress[msg.job_id]
              const completedJobIds = msg.job_id
                ? { ...prev.completedJobIds, [msg.job_id]: true as const }
                : prev.completedJobIds
              return { progressMap, jobProgress, completedJobIds }
            })
            qc.invalidateQueries({ queryKey: ['library'] })
            qc.invalidateQueries({ queryKey: ['library-processing'] })
            qc.invalidateQueries({ queryKey: ['library-stats'] })

          } else if (msg.type === 'error') {
            setState(prev => {
              const progressMap = { ...prev.progressMap }
              delete progressMap[msg.media_id]
              const jobProgress = { ...prev.jobProgress }
              if (msg.job_id) delete jobProgress[msg.job_id]
              return { ...prev, progressMap, jobProgress }
            })
            qc.invalidateQueries({ queryKey: ['library-processing'] })
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onerror = () => {
        // Clear ALL handlers before closing so onclose doesn't also fire a reconnect
        clearHandlers(ws)
        // Only close if not already closing/closed
        if (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN) {
          ws.close()
        }
        if (!mountedRef.current) return
        // Schedule reconnect with back-off (max 30s)
        retryDelay.current = Math.min(retryDelay.current * 1.5, 30_000)
        reconnectTimer.current = setTimeout(connect, retryDelay.current)
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        reconnectTimer.current = setTimeout(connect, retryDelay.current)
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        clearHandlers(wsRef.current)
        // Only call close() when OPEN — calling it while CONNECTING generates a
        // "WebSocket closed before connection established" browser console error
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close()
        }
      }
    }
  }, [qc])

  return state
}
