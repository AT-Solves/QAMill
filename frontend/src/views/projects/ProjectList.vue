<template>
  <div class="projects-page">
    <div class="page-header">
      <h1>Projects</h1>
      <button @click="showCreateModal = true" class="primary-button">
        + New Project
      </button>
    </div>

    <div class="projects-container">
      <div v-if="projects.length === 0" class="empty-state">
        <h2>No projects yet</h2>
        <p>Create your first project to start mutation testing</p>
        <button @click="showCreateModal = true" class="primary-button">Create Project</button>
      </div>

      <div v-else class="projects-grid">
        <div v-for="project in projects" :key="project.id" class="project-card" @contextmenu.prevent="showProjectMenu">
          <div class="card-header">
            <h3>{{ project.name }}</h3>
            <span class="menu-button">⋮</span>
          </div>
          <p class="description">{{ project.description || 'No description' }}</p>
          <div class="project-details">
            <div class="detail">
              <span class="label">Languages:</span>
              <span class="value">{{ project.languages.join(', ') }}</span>
            </div>
            <div class="detail">
              <span class="label">Tests:</span>
              <span class="value">{{ project.frameworks.join(', ') }}</span>
            </div>
          </div>
          <router-link :to="`/projects/${project.id}`" class="view-button">
            View Project →
          </router-link>
        </div>
      </div>
    </div>

    <!-- Create Project Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h2>Create New Project</h2>
          <button @click="showCreateModal = false" class="close-button">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label>Project Name</label>
            <input v-model="newProject.name" type="text" placeholder="My awesome project" />
          </div>
          <div class="form-group">
            <label>Description</label>
            <textarea v-model="newProject.description" placeholder="What does this project do?"></textarea>
          </div>
          <div class="form-group">
            <label>Languages</label>
            <div class="checkbox-group">
              <label>
                <input type="checkbox" value="python" v-model="newProject.languages" /> Python
              </label>
              <label>
                <input type="checkbox" value="javascript" v-model="newProject.languages" /> JavaScript
              </label>
              <label>
                <input type="checkbox" value="csharp" v-model="newProject.languages" /> C#
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateModal = false" class="secondary-button">Cancel</button>
          <button @click="createProject" class="primary-button">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const projects = ref([])
const showCreateModal = ref(false)
const newProject = ref({
  name: '',
  description: '',
  languages: ['python'],
  frameworks: ['pytest'],
})

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/projects')
    const data = await res.json()
    projects.value = data.projects || []
  } catch (error) {
    console.error('Error loading projects:', error)
  }
})

const createProject = async () => {
  try {
    const res = await fetch('/api/v1/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProject.value),
    })
    if (res.ok) {
      const created = await res.json()
      projects.value.push(created)
      showCreateModal.value = false
      newProject.value = {
        name: '',
        description: '',
        languages: ['python'],
        frameworks: ['pytest'],
      }
    }
  } catch (error) {
    console.error('Error creating project:', error)
  }
}

const showProjectMenu = (event: MouseEvent) => {
  // Context menu implementation
  console.log('Project context menu')
}
</script>

<style scoped>
.projects-page {
  padding: 40px;
  margin-left: 280px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 40px;
}

.page-header h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
}

.projects-container {
  width: 100%;
}

.empty-state {
  text-align: center;
  padding: 80px 40px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.empty-state h2 {
  margin: 0 0 10px 0;
  font-size: 24px;
}

.empty-state p {
  margin: 0 0 30px 0;
  color: #7f8c8d;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.project-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.project-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.menu-button {
  cursor: pointer;
  font-size: 20px;
  color: #bdc3c7;
}

.menu-button:hover {
  color: #667eea;
}

.description {
  color: #7f8c8d;
  margin: 0 0 16px 0;
  font-size: 14px;
  line-height: 1.5;
}

.project-details {
  flex: 1;
  margin-bottom: 16px;
}

.detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 13px;
}

.detail .label {
  color: #7f8c8d;
  font-weight: 500;
}

.detail .value {
  color: #2c3e50;
  font-weight: 600;
}

.view-button {
  display: block;
  text-align: center;
  padding: 10px;
  background-color: #f0f1f3;
  color: #667eea;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}

.view-button:hover {
  background-color: #667eea;
  color: white;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid #ecf0f1;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #7f8c8d;
}

.modal-content {
  padding: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  font-size: 14px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ecf0f1;
  border-radius: 6px;
  font-family: inherit;
  font-size: 14px;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-weight: 400;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px;
  border-top: 1px solid #ecf0f1;
}

.primary-button {
  padding: 10px 20px;
  background-color: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: background-color 0.2s;
}

.primary-button:hover {
  background-color: #764ba2;
}

.secondary-button {
  padding: 10px 20px;
  background-color: #f0f1f3;
  color: #2c3e50;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: background-color 0.2s;
}

.secondary-button:hover {
  background-color: #ecf0f1;
}
</style>
