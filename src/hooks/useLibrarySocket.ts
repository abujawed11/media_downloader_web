import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { BASE_URL } from '../lib/config'

type WSMessage =
  | { type: 'progress'; media_id: string; percent: number }
  | { type: 'complete'; media_id: string }
  | { type: 'error'; media_id: string }

/** Derives ws(s)://host:port from the HTTP BASE_URL. */
function wsUrl(): string {
  return BASE_URL.replace(/^http/, 'ws') + '/ws/library'
}

/**
 * Connects to the backend WebSocket and returns a live map of
 * { [media_id]: percent } for in-progress uploads.
 *
 * Also invalidates React-Query caches automatically when an upload
 * completes or errors, so the Library grid refreshes without a page reload.
 */
export function useLibrarySocket(): Record<string, number> {
  const qc = useQueryClient()
  const [progressMap, setProgressMap] = useState<Record<string, number>>({})
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true

    function connect() {
      const ws = new WebSocket(wsUrl())
      wsRef.current = ws

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return
        try {
          const msg: WSMessage = JSON.parse(event.data as string)

          if (msg.type === 'progress') {
            setProgressMap(prev => ({ ...prev, [msg.media_id]: msg.percent }))
          } else if (msg.type === 'complete') {
            // Remove from progress map and refresh the library grid
            setProgressMap(prev => {
              const next = { ...prev }
              delete next[msg.media_id]
              return next
            })
            qc.invalidateQueries({ queryKey: ['library'] })
            qc.invalidateQueries({ queryKey: ['library-processing'] })
            qc.invalidateQueries({ queryKey: ['library-stats'] })
          } else if (msg.type === 'error') {
            setProgressMap(prev => {
              const next = { ...prev }
              delete next[msg.media_id]
              return next
            })
            qc.invalidateQueries({ queryKey: ['library-processing'] })
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        // Auto-reconnect after 3 s
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect loop on intentional unmount
        wsRef.current.close()
      }
    }
  }, [qc]) // qc reference is stable

  return progressMap
}
