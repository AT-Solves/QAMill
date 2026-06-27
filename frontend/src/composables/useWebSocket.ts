import { ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export function useWebSocket(url: string) {
  const authStore = useAuthStore()
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const messages = ref<WebSocketMessage[]>([])
  const error = ref<string>('')

  const connect = () => {
    if (!authStore.accessToken) {
      error.value = 'No authentication token'
      return
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}${url}?token=${authStore.accessToken}`

      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        isConnected.value = true
        error.value = ''
        console.log('WebSocket connected')
      }

      ws.value.onmessage = (event) => {
        const message = JSON.parse(event.data)
        messages.value.push(message)
      }

      ws.value.onerror = (event) => {
        error.value = 'WebSocket error'
        isConnected.value = false
        console.error('WebSocket error:', event)
      }

      ws.value.onclose = () => {
        isConnected.value = false
        console.log('WebSocket disconnected')
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Connection failed'
      isConnected.value = false
    }
  }

  const send = (message: any) => {
    if (ws.value && isConnected.value) {
      ws.value.send(JSON.stringify(message))
    }
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
    }
  }

  const clearMessages = () => {
    messages.value = []
  }

  const getLastMessage = (): WebSocketMessage | null => {
    return messages.value.length > 0
      ? messages.value[messages.value.length - 1]
      : null
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    isConnected,
    messages,
    error,
    connect,
    send,
    disconnect,
    clearMessages,
    getLastMessage,
  }
}
