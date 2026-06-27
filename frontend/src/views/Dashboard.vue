<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <h1>Dashboard</h1>
      <p class="subtitle">Test Quality Governance & Mutation Analysis</p>
    </div>

    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-icon">📊</div>
        <div class="metric-content">
          <div class="metric-label">Active Projects</div>
          <div class="metric-value">{{ activeProjects }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon">🔬</div>
        <div class="metric-content">
          <div class="metric-label">Analyses This Week</div>
          <div class="metric-value">{{ analysesThisWeek }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon">✅</div>
        <div class="metric-content">
          <div class="metric-label">Avg Mutation Score</div>
          <div class="metric-value">{{ avgMutationScore }}%</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon">🎯</div>
        <div class="metric-content">
          <div class="metric-label">Total Coverage</div>
          <div class="metric-value">{{ totalCoverage }}%</div>
        </div>
      </div>
    </div>

    <div class="dashboard-sections">
      <section class="section">
        <div class="section-header">
          <h2>Recent Projects</h2>
          <router-link to="/projects" class="link-button">View All →</router-link>
        </div>
        <div class="projects-list">
          <div v-if="projects.length === 0" class="empty-state">
            <p>No projects yet</p>
            <router-link to="/projects" class="primary-button">Create Project</router-link>
          </div>
          <div v-for="project in projects" :key="project.id" class="project-item" @contextmenu.prevent="showContextMenu">
            <div class="project-info">
              <h3>{{ project.name }}</h3>
              <p>{{ project.description }}</p>
              <div class="project-meta">
                <span class="badge">{{ project.languages.join(', ') }}</span>
              </div>
            </div>
            <router-link :to="`/projects/${project.id}`" class="arrow">→</router-link>
          </div>
        </div>
      </section>

      <section class="section">
        <div class="section-header">
          <h2>Recent Analyses</h2>
        </div>
        <div class="analyses-list">
          <div v-if="recentAnalyses.length === 0" class="empty-state">
            <p>No analyses yet</p>
          </div>
          <div v-for="analysis in recentAnalyses" :key="analysis.id" class="analysis-item">
            <div class="analysis-info">
              <h4>{{ analysis.file_path }}</h4>
              <div class="analysis-meta">
                <span class="badge">{{ analysis.language }}</span>
                <span class="status" :class="analysis.status">{{ analysis.status }}</span>
              </div>
            </div>
            <div class="analysis-score">
              <div class="score-value">{{ analysis.mutation_score.toFixed(1) }}%</div>
              <div class="score-label">Mutation</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const activeProjects = ref(0)
const analysesThisWeek = ref(0)
const avgMutationScore = ref(0)
const totalCoverage = ref(0)
const projects = ref([])
const recentAnalyses = ref([])

onMounted(async () => {
  // Load dashboard data from API
  try {
    // Fetch projects
    const projectsRes = await fetch('/api/v1/projects')
    const projectsData = await projectsRes.json()
    projects.value = projectsData.projects || []
    activeProjects.value = projects.value.length

    // Fetch stats for each project and calculate averages
    if (projects.value.length > 0) {
      let totalScore = 0
      let totalCov = 0
      for (const project of projects.value) {
        const statsRes = await fetch(`/api/v1/projects/${project.id}/stats`)
        const stats = await statsRes.json()
        totalScore += stats.avg_mutation_score || 0
        totalCov += stats.avg_coverage_score || 0
      }
      avgMutationScore.value = Math.round(totalScore / projects.value.length)
      totalCoverage.value = Math.round(totalCov / projects.value.length)
    }

    // Fetch recent analyses from first project
    if (projects.value.length > 0) {
      const analysesRes = await fetch(`/api/v1/projects/${projects.value[0].id}/analyses?limit=5`)
      const analysesData = await analysesRes.json()
      recentAnalyses.value = analysesData.analyses || []
      analysesThisWeek.value = recentAnalyses.value.length
    }
  } catch (error) {
    console.error('Error loading dashboard:', error)
  }
})

const showContextMenu = (event: MouseEvent) => {
  // Context menu implementation
  console.log('Context menu at:', event.clientX, event.clientY)
}
</script>

<style scoped>
.dashboard {
  padding: 40px;
  margin-left: 280px;
  max-width: 1400px;
}

.dashboard-header {
  margin-bottom: 40px;
}

.dashboard-header h1 {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 10px 0;
}

.subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin: 0;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 40px;
}

.metric-card {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.2s;
}

.metric-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.metric-icon {
  font-size: 32px;
}

.metric-content {
  flex: 1;
}

.metric-label {
  font-size: 12px;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
}

.dashboard-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1200px) {
  .dashboard-sections {
    grid-template-columns: 1fr;
  }
}

.section {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f1f3;
}

.section h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.link-button {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: color 0.2s;
}

.link-button:hover {
  color: #764ba2;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #7f8c8d;
}

.empty-state p {
  margin: 0 0 16px 0;
}

.projects-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #ecf0f1;
  border-radius: 8px;
  transition: all 0.2s;
  cursor: pointer;
}

.project-item:hover {
  border-color: #667eea;
  background-color: #f8f9ff;
}

.project-info h3 {
  margin: 0 0 4px 0;
  font-size: 15px;
  font-weight: 600;
}

.project-info p {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #7f8c8d;
}

.project-meta {
  display: flex;
  gap: 8px;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  background-color: #f0f1f3;
  color: #2c3e50;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.arrow {
  color: #667eea;
  font-size: 20px;
  text-decoration: none;
}

.analyses-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analysis-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #ecf0f1;
  border-radius: 8px;
}

.analysis-info h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.analysis-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}

.status {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status.completed {
  background-color: #d4edda;
  color: #155724;
}

.status.pending {
  background-color: #fff3cd;
  color: #856404;
}

.status.running {
  background-color: #d1ecf1;
  color: #0c5460;
}

.analysis-score {
  text-align: center;
}

.score-value {
  font-size: 20px;
  font-weight: 700;
  color: #667eea;
}

.score-label {
  font-size: 12px;
  color: #7f8c8d;
}

.primary-button {
  display: inline-block;
  padding: 8px 16px;
  background-color: #667eea;
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.2s;
}

.primary-button:hover {
  background-color: #764ba2;
}
</style>
