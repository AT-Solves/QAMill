<template>
  <div class="project-detail">
    <div class="page-header">
      <div>
        <h1>{{ project?.name || 'Project' }}</h1>
        <p>{{ project?.description }}</p>
      </div>
      <button @click="startAnalysis" class="primary-button">🔬 Run Analysis</button>
    </div>

    <div class="tabs">
      <button v-for="tab in tabs" :key="tab" @click="activeTab = tab" :class="{ active: activeTab === tab }">
        {{ tab }}
      </button>
    </div>

    <div class="tab-content">
      <section v-if="activeTab === 'Overview'" class="overview">
        <h2>Project Overview</h2>
        <div class="info-grid">
          <div class="info-card">
            <div class="label">Languages</div>
            <div class="value">{{ project?.languages?.join(', ') }}</div>
          </div>
          <div class="info-card">
            <div class="label">Test Frameworks</div>
            <div class="value">{{ project?.frameworks?.join(', ') }}</div>
          </div>
          <div class="info-card">
            <div class="label">Total Analyses</div>
            <div class="value">{{ totalAnalyses }}</div>
          </div>
          <div class="info-card">
            <div class="label">Avg Score</div>
            <div class="value">{{ avgScore }}%</div>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'Analyses'" class="analyses">
        <h2>Analysis History</h2>
        <div class="analyses-list">
          <div v-for="analysis in analyses" :key="analysis.id" class="analysis-row">
            <div>
              <h4>{{ analysis.file_path }}</h4>
              <p>{{ analysis.status }}</p>
            </div>
            <div class="score">{{ analysis.mutation_score.toFixed(1) }}%</div>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'Settings'" class="settings">
        <h2>Project Settings</h2>
        <p>Settings configuration goes here</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const projectId = route.params.projectId as string

const project = ref<any>(null)
const analyses = ref([])
const activeTab = ref('Overview')
const tabs = ['Overview', 'Analyses', 'Settings', 'Team']
const totalAnalyses = ref(0)
const avgScore = ref(0)

onMounted(async () => {
  try {
    const res = await fetch(`/api/v1/projects/${projectId}`)
    project.value = await res.json()

    const statsRes = await fetch(`/api/v1/projects/${projectId}/stats`)
    const stats = await statsRes.json()
    totalAnalyses.value = stats.total_analyses
    avgScore.value = Math.round(stats.avg_mutation_score)

    const analysesRes = await fetch(`/api/v1/projects/${projectId}/analyses`)
    const analysesData = await analysesRes.json()
    analyses.value = analysesData.analyses || []
  } catch (error) {
    console.error('Error loading project:', error)
  }
})

const startAnalysis = () => {
  alert('Analysis feature coming soon!')
}
</script>

<style scoped>
.project-detail {
  padding: 40px;
  margin-left: 280px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 40px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  font-size: 32px;
}

.page-header p {
  margin: 0;
  color: #7f8c8d;
}

.tabs {
  display: flex;
  gap: 20px;
  border-bottom: 2px solid #ecf0f1;
  margin-bottom: 30px;
}

.tabs button {
  padding: 12px 0;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-weight: 600;
  color: #7f8c8d;
  transition: all 0.2s;
}

.tabs button.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.info-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.label {
  color: #7f8c8d;
  font-size: 12px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.value {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.analyses-list {
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.analysis-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ecf0f1;
}

.analysis-row:last-child {
  border-bottom: none;
}

.analysis-row h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
}

.analysis-row p {
  margin: 0;
  font-size: 12px;
  color: #7f8c8d;
}

.score {
  font-size: 18px;
  font-weight: 700;
  color: #667eea;
}

.primary-button {
  padding: 10px 20px;
  background-color: #667eea;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
}

.primary-button:hover {
  background-color: #764ba2;
}
</style>
