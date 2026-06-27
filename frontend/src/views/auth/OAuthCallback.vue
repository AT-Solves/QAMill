<template>
  <div class="oauth-callback-page">
    <div class="container">
      <h2>Completing {{ provider }} login...</h2>
      <p class="subtitle">Please wait while we authenticate you</p>

      <div class="spinner">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>

      <div v-if="error" class="error-message">
        <p>Authentication failed</p>
        <p class="error-detail">{{ error }}</p>
        <router-link to="/login" class="back-link">Back to Login</router-link>
      </div>

      <div v-if="loading" class="status-message">
        <p>{{ statusMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const provider = ref('OAuth')
const loading = ref(true)
const error = ref('')
const statusMessage = ref('Authenticating...')

onMounted(async () => {
  try {
    // Determine provider from route
    const pathProvider = route.params.provider as string
    provider.value = pathProvider === 'github' ? 'GitHub' : 'Google'

    // Get authorization code from URL
    const code = route.query.code as string
    if (!code) {
      throw new Error('No authorization code received')
    }

    statusMessage.value = `Authenticating with ${provider.value}...`

    // Exchange code for tokens
    const response = await fetch(
      `/api/v1/oauth/${pathProvider}/callback?code=${code}`,
      {
        method: 'POST',
      }
    )

    if (!response.ok) {
      throw new Error(`Authentication failed: ${response.statusText}`)
    }

    const data = await response.json()

    statusMessage.value = 'Signing you in...'

    // Store tokens
    authStore.accessToken = data.access_token
    authStore.refreshToken = data.refresh_token

    statusMessage.value = 'Loading profile...'

    // Fetch user profile
    await authStore.fetchProfile()

    loading.value = false
    statusMessage.value = 'Redirecting...'

    // Redirect to dashboard
    setTimeout(() => {
      router.push('/')
    }, 1000)
  } catch (err) {
    loading.value = false
    error.value = err instanceof Error ? err.message : 'Authentication failed'
    console.error('OAuth callback error:', err)
  }
})
</script>

<style scoped>
.oauth-callback-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.container {
  text-align: center;
  background: white;
  padding: 60px 40px;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

h2 {
  color: #2c3e50;
  margin-bottom: 10px;
  font-size: 24px;
}

.subtitle {
  color: #7f8c8d;
  margin-bottom: 40px;
  font-size: 14px;
}

.spinner {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin: 40px 0;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #667eea;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 20px;
  border-radius: 6px;
  margin-top: 30px;
}

.error-message p {
  margin: 10px 0;
}

.error-detail {
  font-size: 12px;
  color: #6c757d;
}

.back-link {
  display: inline-block;
  margin-top: 15px;
  padding: 10px 20px;
  background-color: #721c24;
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  transition: background-color 0.2s;
}

.back-link:hover {
  background-color: #5a151b;
}

.status-message {
  color: #667eea;
  font-weight: 500;
  margin-top: 30px;
}
</style>
