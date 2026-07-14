<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { logout } from '@/services/auth'

interface Dhis2User {
    id: string | null
    email: string | null
    username: string | null
    displayName: string | null
}

const user = ref<Dhis2User | null>(null)
const error = ref('')

onMounted(() => {
    const authStore = useAuthStore()
    user.value = authStore.user
})
</script>

<template>
<div class="profile-container">
     <h2>Parameters - Profile</h2>
    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="user" class="profile-card">
      <p><strong>ID:</strong> {{ user.id || 'N/A' }}</p>
      <p><strong>Email:</strong> {{ user.email || 'N/A' }}</p>
      <p><strong>Username:</strong> {{ user.username || 'N/A' }}</p>
      <p><strong>Display Name:</strong> {{ user.displayName || 'N/A' }}</p>
      <button @click="logout" class="logout-btn">Logout</button>
    </div>
  </div>
</template>

<style scoped>
.profile-container {
  max-width: 500px;
  margin: 0 auto;
  padding: 2rem;
  color: white;
}

.profile-card {
  padding: 1.5rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.logout-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.logout-btn:hover {
  background: #dc2626;
}

.error-message {
  background: #fee;
  color: #c00;
  padding: 0.5rem;
  border-radius: 4px;
}
</style>