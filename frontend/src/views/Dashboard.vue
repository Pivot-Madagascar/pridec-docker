<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Dashboard</h1>
    </div>
    
    <!-- Metrics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm">Total Records</p>
            <p class="text-2xl font-bold text-white">1,234,567</p>
          </div>
          <Database class="w-8 h-8 text-blue-400" />
        </div>
      </div>
      
      <div class="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm">Active Jobs</p>
            <p class="text-2xl font-bold text-white">23</p>
          </div>
          <Activity class="w-8 h-8 text-green-400" />
        </div>
      </div>
      
      <div class="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm">Success Rate</p>
            <p class="text-2xl font-bold text-white">98.5%</p>
          </div>
          <TrendingUp class="w-8 h-8 text-green-400" />
        </div>
      </div>
      
      <div class="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-gray-400 text-sm">Errors</p>
            <p class="text-2xl font-bold text-white">12</p>
          </div>
          <AlertTriangle class="w-8 h-8 text-red-400" />
        </div>
      </div>
    </div>
    
    <!-- Recent Activity -->
    <div class="bg-gray-800 rounded-lg border border-gray-700">
      <div class="p-6 border-b border-gray-700">
        <h2 class="text-xl font-semibold text-white">Recent Activity</h2>
      </div>
      <div class="p-6">
        <div class="space-y-4">
          <div class="flex items-center space-x-4">
            <div class="w-2 h-2 bg-green-400 rounded-full"></div>
            <span class="text-gray-300">Data sync completed for customer_data table</span>
            <span class="text-gray-500 text-sm ml-auto">2 mins ago</span>
          </div>
          <div class="flex items-center space-x-4">
            <div class="w-2 h-2 bg-blue-400 rounded-full"></div>
            <span class="text-gray-300">Forecast model training started</span>
            <span class="text-gray-500 text-sm ml-auto">5 mins ago</span>
          </div>
          <div class="flex items-center space-x-4">
            <div class="w-2 h-2 bg-orange-400 rounded-full"></div>
            <span class="text-gray-300">Monthly report generated</span>
            <span class="text-gray-500 text-sm ml-auto">1 hour ago</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Database, Activity, TrendingUp, AlertTriangle } from 'lucide-vue-next'
</script>