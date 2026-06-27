<template>
  <div class="settings-page">
    <h1>Settings</h1>

    <div class="settings-container">
      <div class="settings-menu">
        <button v-for="tab in tabs" :key="tab" @click="activeTab = tab" :class="{ active: activeTab === tab }">
          {{ tab }}
        </button>
      </div>

      <div class="settings-content">
        <section v-if="activeTab === 'Account'">
          <h2>Account Settings</h2>
          <p>Manage your account information</p>
        </section>

        <section v-if="activeTab === 'Organization'">
          <h2>Organization</h2>
          <p>Manage your organization settings</p>
        </section>

        <section v-if="activeTab === 'API Keys'">
          <h2>API Keys</h2>
          <p>Manage your API keys and integrations</p>
        </section>

        <section v-if="activeTab === 'Billing'">
          <h2>Billing</h2>
          <p>Manage your billing and subscription</p>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activeTab = ref('Account')
const tabs = ['Account', 'Organization', 'API Keys', 'Billing']
</script>

<style scoped>
.settings-page {
  padding: 40px;
  margin-left: 280px;
}

.settings-page h1 {
  margin-bottom: 30px;
}

.settings-container {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 30px;
}

.settings-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.settings-menu button {
  text-align: left;
  padding: 12px 16px;
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  color: #7f8c8d;
  transition: all 0.2s;
}

.settings-menu button:hover {
  background-color: #f0f1f3;
  color: #2c3e50;
}

.settings-menu button.active {
  background-color: #667eea;
  color: white;
}

.settings-content {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.settings-content h2 {
  margin-top: 0;
}
</style>
