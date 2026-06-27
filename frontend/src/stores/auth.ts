import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<any>(null)
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')
  const isLoading = ref(false)
  const error = ref<string>('')

  // Load from localStorage on init
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem('auth')
    if (stored) {
      const parsed = JSON.parse(stored)
      user.value = parsed.user
      accessToken.value = parsed.accessToken
      refreshToken.value = parsed.refreshToken
    }
  }

  // Computed
  const isAuthenticated = computed(() => !!accessToken.value)
  const authHeader = computed(() =>
    accessToken.value ? `Bearer ${accessToken.value}` : ''
  )

  // Methods
  const login = async (email: string, password: string) => {
    isLoading.value = true
    error.value = ''

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        throw new Error('Login failed')
      }

      const data = await response.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token

      // Fetch user profile
      await fetchProfile()

      // Save to localStorage
      saveToLocalStorage()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Login failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const signup = async (
    email: string,
    password: string,
    name: string
  ) => {
    isLoading.value = true
    error.value = ''

    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name }),
      })

      if (!response.ok) {
        throw new Error('Signup failed')
      }

      const data = await response.json()
      user.value = {
        id: data.user_id,
        email: data.email,
        name: data.name,
      }
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token

      saveToLocalStorage()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Signup failed'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchProfile = async () => {
    try {
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          Authorization: authHeader.value,
        },
      })

      if (response.ok) {
        user.value = await response.json()
      }
    } catch (err) {
      console.error('Error fetching profile:', err)
    }
  }

  const refreshAccessToken = async () => {
    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })

      if (!response.ok) {
        throw new Error('Token refresh failed')
      }

      const data = await response.json()
      accessToken.value = data.access_token

      saveToLocalStorage()
    } catch (err) {
      logout()
      throw err
    }
  }

  const logout = () => {
    user.value = null
    accessToken.value = ''
    refreshToken.value = ''
    error.value = ''

    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth')
    }
  }

  const saveToLocalStorage = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(
        'auth',
        JSON.stringify({
          user: user.value,
          accessToken: accessToken.value,
          refreshToken: refreshToken.value,
        })
      )
    }
  }

  return {
    // State
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Computed
    isAuthenticated,
    authHeader,

    // Methods
    login,
    signup,
    fetchProfile,
    refreshAccessToken,
    logout,
  }
})
