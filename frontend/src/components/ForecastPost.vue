<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
    <div class="w-full max-w-2xl p-8 space-y-6 bg-white/80 backdrop-blur-md rounded-3xl shadow-xl shadow-black/5 border border-white/20 relative overflow-hidden">
      <!-- Decorative gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-b from-purple-500/5 to-pink-500/10 pointer-events-none"></div>

      <div class="relative z-10">
        <!-- Header -->
        <div class="flex items-center justify-center space-x-3 mb-6">
          <div class="w-10 h-10 bg-gradient-to-br from-purple-600 via-pink-600 to-indigo-700 rounded-xl flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-purple-500/30 ring-2 ring-white/20">
            PF
          </div>
          <div class="font-bold text-gray-800 text-xl bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Post Forecast
          </div>
        </div>

        <!-- Forecast textarea -->
        <textarea
          v-model="forecast"
          placeholder="Enter forecast JSON"
          class="w-full h-40 p-4 rounded-xl border border-white/20 bg-white/50 backdrop-blur-sm shadow-inner text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-400 transition-all duration-300"
        ></textarea>

        <!-- Dry Run Checkbox -->
        <div class="mt-4">
          <label class="inline-flex items-center text-gray-700 font-medium">
            <input type="checkbox" v-model="dryRun" class="mr-2 rounded border-white/20 bg-white/50 shadow-inner focus:ring-2 focus:ring-purple-400 transition-all duration-300">
            <span>Dry Run</span>
          </label>
        </div>

        <!-- Submit Button -->
        <button
          @click="submit"
          class="relative px-6 py-3 mt-4 bg-gradient-to-r from-purple-600 via-pink-600 to-indigo-700 hover:from-pink-600 hover:via-indigo-700 hover:to-purple-700 text-white rounded-xl font-semibold transition-all duration-300 flex items-center justify-center shadow-lg shadow-purple-500/30 hover:shadow-xl hover:shadow-purple-500/40 hover:-translate-y-0.5 overflow-hidden"
        >
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] hover:translate-x-[100%] transition-transform duration-700"></div>
          <span>🚀 Submit Forecast</span>
        </button>

        <!-- Response Display -->
        <div v-if="response" class="mt-4 p-4 bg-white/70 backdrop-blur-sm border border-white/20 rounded-xl shadow-inner overflow-auto max-h-64">
          <pre class="text-sm text-gray-700">{{ JSON.stringify(response, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      forecast: '{}',
      dryRun: true,
      response: null
    };
  },
  methods: {
    async submit() {
      try {
        const payload = {
          forecast_data: JSON.parse(this.forecast),
          dry_run: this.dryRun
        };
        const res = await axios.post('/api/post/forecast', payload);
        this.response = res.data;
      } catch (e) {
        this.response = { error: e.message };
      }
    }
  }
};
</script>
