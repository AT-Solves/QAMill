<template>
  <div class="analysis-detail">
    <h1>Analysis Results</h1>
    <p>Analysis ID: {{ analysisId }}</p>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const analysisId = route.params.analysisId as string
</script>

<style scoped>
.analysis-detail {
  padding: 40px;
  margin-left: 280px;
}
</style>
