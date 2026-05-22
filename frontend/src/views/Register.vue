<template>
  <div class="flex items-center justify-center min-h-screen amazon-gradient transition-colors duration-200">
    <div class="amazon-card bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg w-full max-w-md transition-colors duration-200">
      <h2 class="text-2xl font-bold text-center text-amazon-dark dark:text-white mb-6">
        Create Account
      </h2>

      <form @submit.prevent="handleRegister" class="space-y-5">
        <!-- Username -->
        <div>
          <label class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">Username</label>
          <input
            v-model="username"
            type="text"
            class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <!-- Email -->
        <div>
          <label class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
          <input
            v-model="email"
            type="email"
            class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <!-- Password -->
        <div>
          <label class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
          <input
            v-model="password"
            type="password"
            minlength="6"
            class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <!-- Confirm Password -->
        <div>
          <label class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">Confirm Password</label>
          <input
            v-model="confirmPassword"
            type="password"
            minlength="6"
            class="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            required
          />
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          class="w-full amazon-button py-2 rounded-md font-semibold transition-all duration-200 hover:opacity-90"
          :disabled="loading"
        >
          {{ loading ? 'Creating...' : 'Create Account' }}
        </button>

        <!-- Messages -->
        <p v-if="error" class="mt-3 text-sm text-center text-red-600 dark:text-red-400">{{ error }}</p>
        <p v-if="success" class="mt-3 text-sm text-center text-green-600 dark:text-green-400">{{ success }}</p>

        <!-- Login link -->
        <p class="mt-4 text-sm text-center text-gray-600 dark:text-gray-400">
          Already have an account?
          <router-link class="text-amazon-orange hover:underline" to="/login">Login</router-link>
        </p>
      </form>
    </div>
  </div>
</template>

<script>
import axios from "axios"

export default {
  data() {
    return {
      username: "",
      email: "",
      password: "",
      confirmPassword: "",
      error: "",
      success: "",
      loading: false,
    }
  },
  methods: {
    async handleRegister() {
      this.error = ""
      this.success = ""
      if (this.password !== this.confirmPassword) {
        this.error = "Passwords do not match"
        return
      }
      this.loading = true
      try {
        await axios.post("/api/auth/register", {
          username: this.username,
          password: this.password,
          email: this.email,
        })
        this.success = "Account created successfully. Redirecting to login..."
        setTimeout(() => this.$router.push("/login"), 1200)
      } catch (err) {
        if (err.response && err.response.data && err.response.data.detail) {
          this.error = err.response.data.detail
        } else {
          this.error = "Registration failed"
        }
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.amazon-gradient {
  background: linear-gradient(to bottom, #f7f7f7, #e6e6e6);
}
.dark .amazon-gradient {
  background: linear-gradient(to bottom, #131921, #232F3E);
}
.amazon-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  border: 1px solid #DDD;
}
.dark .amazon-card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  border: 1px solid #444;
}
.amazon-button {
  background: linear-gradient(to bottom, #f7dfa5, #f0c14b);
  border: 1px solid #a88734;
  color: #111;
}
.dark .amazon-button {
  background: linear-gradient(to bottom, #565656, #444);
  border: 1px solid #333;
  color: #fff;
}
</style>
