import { useAuthStore } from '@/stores/auth'

const API_BASE = '/api'

export class ApiClient {
  static async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const authStore = useAuthStore()

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (authStore.authHeader) {
      headers['Authorization'] = authStore.authHeader
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    })

    // Handle token expiration
    if (response.status === 401) {
      try {
        await authStore.refreshAccessToken()
        // Retry with new token
        headers['Authorization'] = authStore.authHeader
        return fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers,
        })
      } catch {
        authStore.logout()
        window.location.href = '/login'
      }
    }

    return response
  }

  static async get<T = any>(endpoint: string): Promise<T> {
    const response = await this.request(endpoint, {
      method: 'GET',
    })
    return response.json()
  }

  static async post<T = any>(
    endpoint: string,
    data?: any
  ): Promise<T> {
    const response = await this.request(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
    return response.json()
  }

  static async put<T = any>(
    endpoint: string,
    data?: any
  ): Promise<T> {
    const response = await this.request(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
    return response.json()
  }

  static async delete<T = any>(endpoint: string): Promise<T> {
    const response = await this.request(endpoint, {
      method: 'DELETE',
    })
    return response.json()
  }
}

export default ApiClient
