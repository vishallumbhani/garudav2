import { useEffect, useRef, useCallback, useState } from 'react'

interface WebSocketOptions {
  onMessage?: (data: any) => void
  onConnect?: () => void
  onDisconnect?: () => void
  reconnectDelay?: number
  maxReconnects?: number
}

interface WebSocketState {
  connected: boolean
  lastEvent: any | null
  reconnectCount: number
}

const WS_BASE = (import.meta.env.VITE_API_URL || 'http://192.168.116.155:8000')
  .replace(/^http/, 'ws')

export const useWebSocket = (path: string, options: WebSocketOptions = {}) => {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    reconnectDelay = 3000,
    maxReconnects = 10,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const [state, setState] = useState<WebSocketState>({
    connected: false,
    lastEvent: null,
    reconnectCount: 0,
  })

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const token = localStorage.getItem('garuda_access_token')
    const url = `${WS_BASE}${path}${token ? `?token=${token}` : ''}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        reconnectCountRef.current = 0
        setState(s => ({ ...s, connected: true, reconnectCount: 0 }))
        onConnect?.()
      }

      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        try {
          const data = JSON.parse(event.data)
          setState(s => ({ ...s, lastEvent: data }))
          onMessage?.(data)
        } catch {}
      }

      ws.onclose = () => {
        if (!mountedRef.current) return
        setState(s => ({ ...s, connected: false }))
        onDisconnect?.()
        // Attempt reconnect
        if (reconnectCountRef.current < maxReconnects) {
          reconnectCountRef.current += 1
          setState(s => ({ ...s, reconnectCount: reconnectCountRef.current }))
          reconnectTimerRef.current = setTimeout(connect, reconnectDelay)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      // WebSocket not available / URL invalid – silently ignore
    }
  }, [path, onMessage, onConnect, onDisconnect, reconnectDelay, maxReconnects])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  return { ...state, send }
}

// Convenience hook: subscribe to live scan events
export const useLiveFeed = (onScan: (event: any) => void, onAlert?: (event: any) => void) => {
  return useWebSocket('/ws/live', {
    onMessage: (data) => {
      if (data.type === 'scan') onScan(data)
      if (data.type === 'alert' && onAlert) onAlert(data)
    },
  })
}
