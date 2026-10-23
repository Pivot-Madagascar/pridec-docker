<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { logout } from '@/services/auth'

const auth = useAuthStore()
</script>

<template>
<div class="profile-container">
     <h2>Parameters - Profile</h2>
    <div v-if="auth.user" class="profile-card">
      <p><strong>ID:</strong> {{ auth.user.id || 'N/A' }}</p>
      <p><strong>Email:</strong> {{ auth.user.email || 'N/A' }}</p>
      <p><strong>Username:</strong> {{ auth.user.username || 'N/A' }}</p>
      <p><strong>Display Name:</strong> {{ auth.user.displayName || 'N/A' }}</p>
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
</style>