<template>
  <nav class="navigation">
    <div class="nav-header">
      <h1 class="logo">QAMill</h1>
    </div>

    <div class="nav-menu">
      <router-link to="/" class="nav-item">
        <span class="icon">📊</span>
        <span>Dashboard</span>
      </router-link>
      <router-link to="/projects" class="nav-item">
        <span class="icon">📦</span>
        <span>Projects</span>
      </router-link>
      <router-link to="/settings" class="nav-item">
        <span class="icon">⚙️</span>
        <span>Settings</span>
      </router-link>
    </div>

    <div class="nav-user">
      <div v-if="authStore.user" class="user-profile" @click="showMenu = !showMenu">
        <div class="avatar">👤</div>
        <div class="user-info">
          <p class="user-name">{{ authStore.user.name }}</p>
          <p class="user-status">Online</p>
        </div>
        <div v-if="showMenu" class="user-menu">
          <router-link to="/settings" class="menu-item">Settings</router-link>
          <button @click="logout" class="menu-item logout-btn">Logout</button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const showMenu = ref(false)

const logout = async () => {
  authStore.logout()
  await router.push('/login')
}
</script>

<style scoped>
.navigation {
  width: 280px;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  position: fixed;
  left: 0;
  top: 0;
  overflow-y: auto;
  z-index: 1000;
}

.nav-header {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  letter-spacing: -0.5px;
}

.nav-menu {
  flex: 1;
  padding: 20px 0;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 15px;
}

.nav-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-item.router-link-active {
  background-color: rgba(255, 255, 255, 0.2);
  color: white;
  font-weight: 600;
}

.icon {
  font-size: 18px;
}

.nav-user {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.user-profile:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.user-info {
  flex: 1;
}

.user-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.user-status {
  margin: 0;
  font-size: 12px;
  opacity: 0.7;
}

.user-menu {
  position: absolute;
  bottom: 60px;
  left: 20px;
  right: 20px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: none;
  text-align: left;
  color: #2c3e50;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.menu-item:hover {
  background-color: #f8f9fa;
}

.logout-btn {
  border-top: 1px solid #ecf0f1;
  color: #e74c3c;
}

.logout-btn:hover {
  background-color: #ffe6e6;
}
</style>
