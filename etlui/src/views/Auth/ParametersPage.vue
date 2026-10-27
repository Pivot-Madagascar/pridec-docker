<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { logout } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

const auth = useAuthStore()
</script>

<template>
<div class="profile-container">
     <h2>Parameters - Profile</h2>
    <Card v-if="auth.user" class="gap-2 p-6">
      <p><strong>ID:</strong> {{ auth.user.id || 'N/A' }}</p>
      <p><strong>Email:</strong> {{ auth.user.email || 'N/A' }}</p>
      <p><strong>Username:</strong> {{ auth.user.username || 'N/A' }}</p>
      <p><strong>Display Name:</strong> {{ auth.user.displayName || 'N/A' }}</p>
      <Button variant="destructive" class="mt-4" @click="logout">Logout</Button>
    </Card>
  </div>
</template>

<style scoped>
.profile-container {
  max-width: 500px;
  margin: 0 auto;
  padding: 2rem;
  color: var(--foreground);
}
</style>