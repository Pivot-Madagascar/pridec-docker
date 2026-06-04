<template>
  <div class="hero-section">
    <h1 class="hero-title">Welcome to PRIDE-C ETL Hub</h1>
    <p class="hero-description">
      Data ingestion, processing, and forecasting platform for malaria surveillance. 
      Manage your ETL pipelines with ease.
    </p>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.hero-section {
  @apply bg-gradient-to-r from-[#131921] to-[#232F3E] rounded-xl p-8 text-white;
}

.hero-title {
  @apply text-4xl font-bold mb-2;
}

.hero-description {
  @apply text-gray-300 text-lg max-w-2xl;
}
</style>