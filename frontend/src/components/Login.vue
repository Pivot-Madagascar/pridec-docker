<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 flex flex-col">
    <!-- Header -->
    <header
      class="bg-amazon-dark text-white px-6 py-4 flex justify-between items-center shadow-md"
    >
      <h1 class="text-lg font-bold">Amazon Clone</h1>
      <div class="flex items-center space-x-4">
        <span
          class="bg-amazon-orange text-amazon-dark text-xs font-bold px-2 py-1 rounded"
        >
          Environment: Development
        </span>
        <button
          @click="toggleDarkMode"
          class="px-3 py-1 bg-amazon-light dark:bg-gray-700 rounded text-sm font-medium"
        >
          {{ isDarkMode ? "Light Mode" : "Dark Mode" }}
        </button>
      </div>
    </header>

    <!-- Content -->
    <main
      class="flex items-center justify-center flex-1 px-4 py-8"
    >
      <div
        class="w-full max-w-sm bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6 space-y-6"
      >
        <!-- Heading -->
        <h2
          class="text-2xl font-semibold text-amazon-dark dark:text-white text-center"
        >
          Sign in
        </h2>

        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username -->
          <div>
            <label
              class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300"
              >Username</label
            >
            <input
              v-model="username"
              type="text"
              class="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange outline-none dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              required
              placeholder="Enter your username"
            />
          </div>

          <!-- Password -->
          <div>
            <label
              class="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300"
              >Password</label
            >
            <input
              v-model="password"
              type="password"
              class="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-amazon-orange focus:border-amazon-orange outline-none dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              required
              placeholder="Enter your password"
            />
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full px-4 py-2 bg-amazon-orange hover:bg-yellow-500 text-amazon-dark font-medium rounded-lg transition-colors duration-200 disabled:opacity-60"
            :disabled="loading"
          >
            {{ loading ? "Signing in..." : "Sign in" }}
          </button>

          <!-- Error -->
          <p v-if="error" class="text-sm text-center text-red-600">
            {{ error }}
          </p>
        </form>

        <!-- Divider -->
        <div class="flex items-center space-x-2">
          <div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
          <span class="text-xs text-gray-500 dark:text-gray-400"
            >New here?</span
          >
          <div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
        </div>

        <!-- Register redirect -->
        <router-link
          to="/register"
          class="block w-full px-4 py-2 text-center bg-amazon-light hover:bg-gray-300 text-amazon-dark rounded-lg text-sm font-medium transition-colors duration-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-white"
        >
          Create your account
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";
import { useRouter } from "vue-router";

const router = useRouter();

const username = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

const isDarkMode = ref(false);

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value;
  document.documentElement.classList.toggle("dark", isDarkMode.value);
};

const handleLogin = async () => {
  error.value = "";
  loading.value = true;
  try {
    const response = await axios.post("/api/auth/login", {
      username: username.value,
      password: password.value,
    });
    const token = response.data.access_token;
    if (!token) {
      throw new Error("Invalid credentials");
    }
    localStorage.setItem("token", token);
    router.push("/dashboard");
  } catch (err) {
    error.value = "Invalid credentials";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
/* Amazon-inspired colors */
:root {
  --amazon-dark: #131921;
  --amazon-orange: #febd69;
  --amazon-light: #f3f3f3;
}
.bg-amazon-dark {
  background-color: var(--amazon-dark);
}
.bg-amazon-orange {
  background-color: var(--amazon-orange);
}
.bg-amazon-light {
  background-color: var(--amazon-light);
}
.text-amazon-dark {
  color: var(--amazon-dark);
}
</style>