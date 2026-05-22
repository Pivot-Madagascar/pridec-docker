<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Forecast History</h1>
    </div>
    
    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <div class="flex items-center space-x-3 mb-6">
        <div class="w-10 h-10 bg-gradient-to-br from-purple-600 via-pink-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-lg">
          FH
        </div>
        <h2 class="text-xl font-semibold text-white">Forecast History</h2>
      </div>

      <!-- History Content -->
      <div v-if="history.length === 0" class="p-6 text-gray-400 text-center bg-gray-900/50 rounded-lg border border-gray-700/50">
        No history available.
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="(entry, index) in history"
          :key="index"
          class="p-4 rounded-lg border border-gray-700 bg-gray-900/50 transition-all hover:bg-gray-900/70"
        >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p class="text-sm text-gray-400">Date</p>
              <p class="text-white">{{ formatDate(entry.timestamp) }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-400">Disease</p>
              <p class="text-white">{{ entry.disease_code }}</p>
            </div>
            <div>
              <p class="text-sm text-gray-400">Type</p>
              <p class="text-white">
                <span :class="entry.dry_run ? 'text-purple-400' : 'text-green-400'">
                  {{ entry.dry_run ? 'Dry Run' : 'Live' }}
                </span>
              </p>
            </div>
            <div>
              <p class="text-sm text-gray-400">Status</p>
              <p class="text-white">
                <span :class="getStatusColor(entry.status)">{{ entry.status }}</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ForecastHistory',
  data() {
    return {
      history: [],
      loading: false,
      error: null
    };
  },
  async mounted() {
    this.loading = true;
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      
      const res = await axios.get('/api/history/forecast');
      this.history = res.data.data.history;
    } catch (e) {
      console.error(e);
      this.error = 'Failed to load forecast history';
    } finally {
      this.loading = false;
    }
  },
  methods: {
    formatDate(timestamp) {
      if (!timestamp) return 'N/A';
      const date = new Date(timestamp);
      return date.toLocaleString();
    },
    getStatusColor(status) {
      const statusColors = {
        'completed': 'text-green-400',
        'success': 'text-green-400',
        'failed': 'text-red-400',
        'running': 'text-yellow-400',
        'pending': 'text-gray-400'
      };
      return statusColors[status.toLowerCase()] || 'text-white';
    }
  }
};
</script>