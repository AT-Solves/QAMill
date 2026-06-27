<template>
  <div class="auth-page">
    <div class="auth-container">
      <h1>Create Account</h1>
      <p>Join QAMill Today</p>

      <form @submit.prevent="signup">
        <div class="form-group">
          <input v-model="name" type="text" placeholder="Full Name" />
        </div>
        <div class="form-group">
          <input v-model="email" type="email" placeholder="Email" />
        </div>
        <div class="form-group">
          <input v-model="password" type="password" placeholder="Password" />
        </div>
        <button type="submit" class="primary-button">Sign Up</button>
      </form>

      <p>Already have an account? <router-link to="/login">Login</router-link></p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const name = ref('')
const email = ref('')
const password = ref('')

const signup = async () => {
  alert('Signup feature coming soon!')
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

.primary-button {
  width: 100%;
  padding: 12px;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
}

.auth-container a {
  color: #667eea;
}
</style>
