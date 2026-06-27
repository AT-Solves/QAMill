<template>
  <div class="oauth-section">
    <div class="divider">
      <span>Or continue with</span>
    </div>

    <div class="oauth-buttons">
      <a href="#" @click.prevent="githubLogin" class="oauth-button github">
        <span class="icon">🐙</span>
        <span>GitHub</span>
      </a>

      <a href="#" @click.prevent="googleLogin" class="oauth-button google">
        <span class="icon">🔍</span>
        <span>Google</span>
      </a>
    </div>

    <div v-if="oauthStatus && !oauthStatus.github_configured && !oauthStatus.google_configured" class="info-message">
      OAuth providers not configured. Use email/password instead.
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const oauthStatus = ref<any>(null)

onMounted(async () => {
  // Check OAuth status
  try {
    const response = await fetch('/api/v1/oauth/status')
    oauthStatus.value = await response.json()
  } catch (error) {
    console.error('Error checking OAuth status:', error)
  }
})

const githubLogin = async () => {
  try {
    const response = await fetch('/api/v1/oauth/github/login')
    const data = await response.json()
    if (data.redirect_url) {
      window.location.href = data.redirect_url
    }
  } catch (error) {
    console.error('GitHub login error:', error)
  }
}

const googleLogin = async () => {
  try {
    const response = await fetch('/api/v1/oauth/google/login')
    const data = await response.json()
    if (data.redirect_url) {
      window.location.href = data.redirect_url
    }
  } catch (error) {
    console.error('Google login error:', error)
  }
}
</script>

<style scoped>
.oauth-section {
  margin-top: 30px;
}

.divider {
  display: flex;
  align-items: center;
  text-align: center;
  margin: 20px 0;
  color: #7f8c8d;
  font-size: 13px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  border-bottom: 1px solid #ecf0f1;
  margin: 0 10px;
}

.oauth-buttons {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.oauth-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid #ecf0f1;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: white;
  color: #2c3e50;
}

.oauth-button:hover {
  border-color: #bdc3c7;
  background-color: #f8f9fa;
}

.oauth-button.github {
  border-color: #333;
}

.oauth-button.github:hover {
  background-color: #f6f8fa;
  border-color: #333;
}

.oauth-button.google {
  border-color: #dadce0;
}

.oauth-button.google:hover {
  background-color: #f8f9fa;
  border-color: #dadce0;
}

.icon {
  font-size: 16px;
}

.info-message {
  background-color: #e8f4f8;
  color: #004d66;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  text-align: center;
  margin-top: 12px;
}
</style>
