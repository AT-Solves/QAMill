<template>
  <div class="auth-page">
    <div class="auth-container">
      <h1>Welcome to QAMill</h1>
      <p>AI-Powered QA Governance Platform</p>

      <form @submit.prevent="handleLogin">
        <div v-if="error" class="error-message">{{ error }}</div>

        <div class="form-group">
          <input
            v-model="email"
            type="email"
            placeholder="Email"
            required
            :disabled="isLoading"
          />
        </div>

        <div class="form-group">
          <input
            v-model="password"
            type="password"
            placeholder="Password"
            required
            :disabled="isLoading"
          />
        </div>

        <button type="submit" class="primary-button" :disabled="isLoading">
          {{ isLoading ? 'Logging in...' : 'Login' }}
        </button>
      </form>

      <OAuthButtons />

      <p>Don't have an account? <router-link to="/signup">Sign up</router-link></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import OAuthButtons from '@/components/OAuthButtons.vue'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref('')

const handleLogin = async () => {
  error.value = ''
  isLoading.value = true

  try {
    await authStore.login(email.value, password.value)
    router.push('/')
  } catch (err) {
    error.value = 'Invalid email or password'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  margin-left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.auth-container {
  background: white;
  padding: 40px;
  border-radius: 12px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.auth-container h1 {
  margin: 0 0 10px 0;
  text-align: center;
}

.auth-container p {
  text-align: center;
  color: #7f8c8d;
  margin-bottom: 30px;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  text-align: center;
}

.form-group {
  margin-bottom: 20px;
}

.form-group input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ecf0f1;
  border-radius: 6px;
  font-size: 14px;
}

.form-group input:disabled {
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.primary-button {
  width: 100%;
  padding: 12px;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.primary-button:hover:not(:disabled) {
  background-color: #764ba2;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-container a {
  color: #667eea;
}
</style>
