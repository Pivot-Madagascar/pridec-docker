<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-white">Data Management</h1>
    </div>
    

    <!-- Upload Sections -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <!-- Polygon Upload Section -->
      <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-3">Polygon Data</h3>
        <p class="text-gray-400 text-sm mb-4">GeoJSON/JSON files</p>

        <!-- Uploaded Card -->
        <div v-if="uploadedPolygon" class="bg-green-900/20 border border-green-600 rounded-lg p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-900/30 rounded flex items-center justify-center">
                <span class="text-xs">📄</span>
              </div>
              <div>
                <p class="text-white font-medium">{{ uploadedPolygon.filename }}</p>
                <p class="text-gray-400 text-sm">{{ formatFileSize(uploadedPolygon.file_size_bytes) }}</p>
              </div>
            </div>
            <button
              @click="deletePolygon"
              class="text-red-400 hover:text-red-300 transition-colors"
              title="Delete file"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Dropzone -->
        <div v-else
          @drop="handlePolygonDrop"
          @dragover.prevent
          @dragenter.prevent
          class="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center transition-colors duration-300 hover:border-blue-500"
          :class="{'border-blue-500 bg-blue-900/10': isDraggingPolygon}"
        >
          <div class="space-y-3">
            <div class="mx-auto w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p class="text-white font-medium text-sm">Drop file here</p>
              <p class="text-gray-400 text-xs">or click to browse</p>
            </div>
            <button
              @click="uploadPolygon"
              :disabled="uploadingPolygon"
              class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {{ uploadingPolygon ? 'Uploading...' : 'Select File' }}
            </button>
          </div>
        </div>
      </div>

      <!-- External Data Upload Section -->
      <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-3">External Data</h3>
        <p class="text-gray-400 text-sm mb-4">CSV files</p>

        <!-- Uploaded Card -->
        <div v-if="uploadedExternalData" class="bg-green-900/20 border border-green-600 rounded-lg p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-900/30 rounded flex items-center justify-center">
                <span class="text-xs">📊</span>
              </div>
              <div>
                <p class="text-white font-medium">{{ uploadedExternalData.filename }}</p>
                <p class="text-gray-400 text-sm">{{ formatFileSize(uploadedExternalData.file_size_bytes) }}</p>
              </div>
            </div>
            <button
              @click="deleteExternalData"
              class="text-red-400 hover:text-red-300 transition-colors"
              title="Delete file"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Dropzone -->
        <div v-else
          @drop="handleExternalDataDrop"
          @dragover.prevent
          @dragenter.prevent
          class="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center transition-colors duration-300 hover:border-blue-500"
          :class="{'border-blue-500 bg-blue-900/10': isDraggingExternalData}"
        >
          <div class="space-y-3">
            <div class="mx-auto w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p class="text-white font-medium text-sm">Drop file here</p>
              <p class="text-gray-400 text-xs">or click to browse</p>
            </div>
            <button
              @click="uploadExternalData"
              :disabled="uploadingExternalData"
              class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {{ uploadingExternalData ? 'Uploading...' : 'Select File' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Config File Upload Section -->
      <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-3">Config File</h3>
        <p class="text-gray-400 text-sm mb-4">JSON files</p>

        <!-- Uploaded Card -->
        <div v-if="uploadedConfigFile" class="bg-green-900/20 border border-green-600 rounded-lg p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <div class="w-8 h-8 bg-green-900/30 rounded flex items-center justify-center">
                <span class="text-xs">⚙️</span>
              </div>
              <div>
                <p class="text-white font-medium">{{ uploadedConfigFile.filename }}</p>
                <p class="text-gray-400 text-sm">{{ formatFileSize(uploadedConfigFile.file_size_bytes) }}</p>
              </div>
            </div>
            <button
              @click="deleteConfigFile"
              class="text-red-400 hover:text-red-300 transition-colors"
              title="Delete file"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Dropzone -->
        <div v-else
          @drop="handleConfigFileDrop"
          @dragover.prevent
          @dragenter.prevent
          class="border-2 border-dashed border-gray-600 rounded-lg p-6 text-center transition-colors duration-300 hover:border-blue-500"
          :class="{'border-blue-500 bg-blue-900/10': isDraggingConfigFile}"
        >
          <div class="space-y-3">
            <div class="mx-auto w-10 h-10 bg-gray-700 rounded-full flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p class="text-white font-medium text-sm">Drop file here</p>
              <p class="text-gray-400 text-xs">or click to browse</p>
            </div>
            <button
              @click="uploadConfigFile"
              :disabled="uploadingConfigFile"
              class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {{ uploadingConfigFile ? 'Uploading...' : 'Select File' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Data Fetch Section -->
    <div class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <h2 class="text-xl font-semibold text-white mb-4">Fetch Data Sources</h2>
      <p class="text-gray-400 mb-6">Select a data source to fetch the latest information.</p>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Climate Data Button -->
        <button
          @click="fetchClimate"
          :disabled="loadingClimate || loadingDisease"
          class="group relative p-4 bg-gray-750 hover:bg-gray-700 border border-gray-600 rounded-lg transition-all duration-300 flex flex-col items-center justify-center space-y-2 overflow-hidden"
          :class="{'opacity-60 cursor-not-allowed': loadingClimate || loadingDisease}"
        >
          <div class="w-10 h-10 rounded-full bg-blue-900/30 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform duration-300">
            <span class="text-xl">🌤️</span>
          </div>
          <span class="font-medium text-white">
            {{ loadingClimate ? "Fetching..." : "Climate Data" }}
          </span>
          <span class="text-xs text-gray-400">Weather and climate information</span>

          <!-- Loading indicator -->
          <div v-if="loadingClimate" class="absolute bottom-0 left-0 h-1 bg-blue-500 animate-progress"></div>
        </button>

        <!-- Disease Data Button -->
        <button
          @click="fetchDisease"
          :disabled="loadingDisease || loadingClimate"
          class="group relative p-4 bg-gray-750 hover:bg-gray-700 border border-gray-600 rounded-lg transition-all duration-300 flex flex-col items-center justify-center space-y-2 overflow-hidden"
          :class="{'opacity-60 cursor-not-allowed': loadingDisease || loadingClimate}"
        >
          <div class="w-10 h-10 rounded-full bg-green-900/30 flex items-center justify-center text-green-400 group-hover:scale-110 transition-transform duration-300">
            <span class="text-xl">🦠</span>
          </div>
          <span class="font-medium text-white">
            {{ loadingDisease ? "Fetching..." : "Disease Data" }}
          </span>
          <span class="text-xs text-gray-400">Health and disease information</span>

          <!-- Loading indicator -->
          <div v-if="loadingDisease" class="absolute bottom-0 left-0 h-1 bg-green-500 animate-progress"></div>
        </button>

        <!-- Forecasting Button -->
        <button
          @click="goToForecasting"
          :disabled="!hasUploaded || loadingClimate || loadingDisease || loadingForecasting"
          class="group relative p-4 bg-gray-750 hover:bg-gray-700 border border-gray-600 rounded-lg transition-all duration-300 flex flex-col items-center justify-center space-y-2 overflow-hidden"
          :class="{'opacity-60 cursor-not-allowed': !hasUploaded || loadingClimate || loadingDisease || loadingForecasting}"
        >
          <div class="w-10 h-10 rounded-full bg-purple-900/30 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform duration-300">
            <span class="text-xl">🔮</span>
          </div>
          <span class="font-medium text-white">
            {{ loadingForecasting ? "Preparing..." : "Go to Forecasting" }}
          </span>
          <span class="text-xs text-gray-400">Fetch all data and run forecast</span>

          <!-- Loading indicator -->
          <div v-if="loadingForecasting" class="absolute bottom-0 left-0 h-1 bg-purple-500 animate-progress"></div>
        </button>
      </div>
    </div>

    <!-- Status Messages -->
    <transition name="fade">
      <div v-if="successMessage" class="bg-green-900/30 border border-green-700/50 rounded-lg p-4">
        <div class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-green-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-green-200">{{ successMessage }}</p>
        </div>
        <p class="text-green-300 text-sm mt-1">{{ completionDetails }}</p>
      </div>
    </transition>
    
    <transition name="fade">
      <div v-if="error" class="bg-red-900/30 border border-red-700/50 rounded-lg p-4">
        <div class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-red-200">{{ error }}</p>
        </div>
        <p class="text-red-300 text-sm mt-1">Please try again or check your connection</p>
      </div>
    </transition>


    <!-- Activity History -->
    <div v-if="activityHistory.length > 0" class="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <h2 class="text-xl font-semibold text-white mb-4">Recent Activity</h2>
      <div class="space-y-3">
        <div v-for="(item, index) in activityHistory" :key="index" 
             class="p-3 rounded-lg border" 
             :class="item.success ? 'bg-green-900/10 border-green-700/30' : 'bg-red-900/10 border-red-700/30'">
          <div class="flex justify-between items-center">
            <span class="font-medium" :class="item.success ? 'text-green-300' : 'text-red-300'">
              {{ item.type }}
            </span>
            <span class="text-xs text-gray-400">{{ item.time }}</span>
          </div>
          <p class="text-sm mt-1" :class="item.success ? 'text-green-200' : 'text-red-200'">
            {{ item.message }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'DataManagement',
  data() {
    return {
      error: null,
      successMessage: null,
      completionDetails: null,
      loadingClimate: false,
      loadingDisease: false,
      loadingForecasting: false,
      activityHistory: [],
      uploadingPolygon: false,
      uploadingExternalData: false,
      uploadingConfigFile: false,
      uploadingTestConfigFile: false,
      hasUploaded: false,
      isDraggingPolygon: false,
      isDraggingExternalData: false,
      isDraggingConfigFile: false,
      uploadedPolygon: null,
      uploadedExternalData: null,
      uploadedConfigFile: null
    };
  },
  mounted() {
  },
  methods: {
    // File handling methods
    handleDrop(e) {
      e.preventDefault();
      this.isDragging = false;
      const files = Array.from(e.dataTransfer.files);
      this.addFiles(files);
    },

    handlePolygonDrop(e) {
      e.preventDefault();
      this.isDraggingPolygon = false;
      const files = Array.from(e.dataTransfer.files);
      this.addPolygonFiles(files);
    },

    handleExternalDataDrop(e) {
      e.preventDefault();
      this.isDraggingExternalData = false;
      const files = Array.from(e.dataTransfer.files);
      this.addExternalDataFiles(files);
    },

    handleConfigFileDrop(e) {
      e.preventDefault();
      this.isDraggingConfigFile = false;
      const files = Array.from(e.dataTransfer.files);
      this.addConfigFiles(files);
    },

    // Test config functionality removed

    
    handleFileSelect(e) {
      const files = Array.from(e.target.files);
      this.addFiles(files);
      e.target.value = ''; // Reset input
    },
    
    addFiles(files) {
      const validFiles = files.filter(file => {
        const validTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/json'];
        const validExtensions = ['.csv', '.xls', '.xlsx', '.json', '.geojson'];
        const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!hasValidExtension && !validTypes.includes(file.type)) {
          this.showError(`Invalid file type: ${file.name}. Only CSV, Excel, JSON, and GeoJSON files are allowed.`);
          return false;
        }

        if (file.size > maxSize) {
          this.showError(`File too large: ${file.name}. Maximum size is 10MB.`);
          return false;
        }

        return true;
      });

      // Avoid duplicates
      const newFiles = validFiles.filter(newFile =>
        !this.selectedFiles.some(existingFile =>
          existingFile.name === newFile.name && existingFile.size === newFile.size
        )
      );

      this.selectedFiles.push(...newFiles);
    },

    addPolygonFiles(files) {
      const validFiles = files.filter(file => {
        const validExtensions = ['.geojson', '.json'];
        const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!hasValidExtension) {
          this.showError(`Invalid file type: ${file.name}. Only GeoJSON and JSON files are allowed.`);
          return false;
        }

        if (file.size > maxSize) {
          this.showError(`File too large: ${file.name}. Maximum size is 10MB.`);
          return false;
        }

        return true;
      });

      if (validFiles.length > 0) {
        this.uploadPolygonFile(validFiles[0]);
      }
    },

    addExternalDataFiles(files) {
      const validFiles = files.filter(file => {
        const validExtensions = ['.csv'];
        const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!hasValidExtension) {
          this.showError(`Invalid file type: ${file.name}. Only CSV files are allowed.`);
          return false;
        }

        if (file.size > maxSize) {
          this.showError(`File too large: ${file.name}. Maximum size is 10MB.`);
          return false;
        }

        return true;
      });

      if (validFiles.length > 0) {
        this.uploadExternalDataFile(validFiles[0]);
      }
    },

    addConfigFiles(files) {
      const validFiles = files.filter(file => {
        const validExtensions = ['.json'];
        const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
        const maxSize = 10 * 1024 * 1024; // 10MB

        if (!hasValidExtension) {
          this.showError(`Invalid file type: ${file.name}. Only JSON files are allowed.`);
          return false;
        }

        if (file.size > maxSize) {
          this.showError(`File too large: ${file.name}. Maximum size is 10MB.`);
          return false;
        }

        return true;
      });

      if (validFiles.length > 0) {
        this.uploadConfigFileFile(validFiles[0]);
      }
    },

    // Test config functionality removed - endpoint not available in new backend

    removeFile(index) {
      this.selectedFiles.splice(index, 1);
    },
    
    clearFiles() {
      this.selectedFiles = [];
    },
    
    
    
    // Existing fetch methods
    async fetchClimate() {
      this.loadingClimate = true;
      this.error = null;
      this.successMessage = null;
      
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found. Please log in again.');
        }
        
        await axios.get('/api/fetch/climate-data');
        
        this.successMessage = 'Climate data fetched successfully!';
        this.completionDetails = `Data fetch completed at ${new Date().toLocaleTimeString()}`;
        
        // Add to activity history
        this.activityHistory.unshift({
          type: 'Climate Data Fetch',
          success: true,
          message: 'Successfully fetched climate data',
          time: new Date().toLocaleTimeString()
        });
        
      } catch (e) {
        console.error('Error fetching climate data:', e);
        this.error = e.response?.data?.message || e.message || 'Failed to fetch climate data';
        
        // Add to activity history
        this.activityHistory.unshift({
          type: 'Climate Data Fetch',
          success: false,
          message: 'Failed to fetch climate data',
          time: new Date().toLocaleTimeString()
        });
      } finally {
        this.loadingClimate = false;
        this.clearMessagesAfterDelay();
        this.limitActivityHistory();
      }
    },
    
    async fetchDisease() {
      this.loadingDisease = true;
      this.error = null;
      this.successMessage = null;

      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found. Please log in again.');
        }

        await axios.get('/api/fetch/disease-data');

        this.successMessage = 'Disease data fetched successfully!';
        this.completionDetails = `Data fetch completed at ${new Date().toLocaleTimeString()}`;

        // Add to activity history
        this.activityHistory.unshift({
          type: 'Disease Data Fetch',
          success: true,
          message: 'Successfully fetched disease data',
          time: new Date().toLocaleTimeString()
        });

      } catch (e) {
        console.error('Error fetching disease data:', e);
        this.error = e.response?.data?.message || e.message || 'Failed to fetch disease data';

        // Add to activity history
        this.activityHistory.unshift({
          type: 'Disease Data Fetch',
          success: false,
          message: 'Failed to fetch disease data',
          time: new Date().toLocaleTimeString()
        });
      } finally {
        this.loadingDisease = false;
        this.clearMessagesAfterDelay();
        this.limitActivityHistory();
      }
    },

    async goToForecasting() {
      this.loadingForecasting = true;
      this.error = null;
      this.successMessage = null;

      try {
        // Fetch all data sources from Redis
        await this.fetchClimate();
        await this.fetchDisease();

        // Redirect to forecasting page
        this.$router.push('/forecasting');

      } catch (e) {
        console.error('Error preparing data for forecasting:', e);
        this.error = e.message || 'Failed to prepare data for forecasting';
      } finally {
        this.loadingForecasting = false;
        this.clearMessagesAfterDelay();
      }
    },

    // Upload methods from Forecasting.vue
    async uploadPolygon() {
      // Create a file input element
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.geojson,.json'
      input.onchange = async (event) => {
        const file = event.target.files?.[0]
        if (!file) return

        this.uploadingPolygon = true
        try {
          const formData = new FormData()
          formData.append('file', file)

          const token = localStorage.getItem('token')
          const headers = token ? { Authorization: `Bearer ${token}` } : {}

          const response = await axios.post('/api/upload/polygon', formData, {
            headers: {
              ...headers,
              'Content-Type': 'multipart/form-data'
            }
          })

          if (response.data.success) {
            this.successMessage = 'Polygon data uploaded successfully'
            this.hasUploaded = true
            this.uploadedPolygon = {
              filename: file.name,
              file_size_bytes: file.size,
              upload_timestamp: new Date().toISOString()
            }
          }
        } catch (error) {
          console.error('Error uploading polygon:', error)
          this.error = 'Error uploading polygon data'
        } finally {
          this.uploadingPolygon = false
        }
      }
      input.click()
    },

    async uploadExternalData() {
      // Create a file input element
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.csv'
      input.onchange = async (event) => {
        const file = event.target.files?.[0]
        if (!file) return

        this.uploadingExternalData = true
        try {
          const formData = new FormData()
          formData.append('file', file)

          const token = localStorage.getItem('token')
          const headers = token ? { Authorization: `Bearer ${token}` } : {}

          const response = await axios.post('/api/upload/external-data', formData, {
            headers: {
              ...headers,
              'Content-Type': 'multipart/form-data'
            }
          })

          if (response.data.success) {
            this.successMessage = 'External data uploaded successfully'
            this.hasUploaded = true
            this.uploadedExternalData = {
              filename: file.name,
              file_size_bytes: file.size,
              upload_timestamp: new Date().toISOString()
            }
          }
        } catch (error) {
          console.error('Error uploading external data:', error)
          this.error = 'Error uploading external data'
        } finally {
          this.uploadingExternalData = false
        }
      }
      input.click()
    },

    async uploadConfigFile() {
      // Create a file input element
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.json'
      input.onchange = async (event) => {
        const file = event.target.files?.[0]
        if (!file) return

        this.uploadingConfigFile = true
        try {
          const formData = new FormData()
          formData.append('file', file)

          const token = localStorage.getItem('token')
          const headers = token ? { Authorization: `Bearer ${token}` } : {}

          const response = await axios.post('/api/upload/config', formData, {
            headers: {
              ...headers,
              'Content-Type': 'multipart/form-data'
            }
          })

          if (response.data.success) {
            this.successMessage = 'Config file uploaded successfully'
            this.hasUploaded = true
            this.uploadedConfigFile = {
              filename: file.name,
              file_size_bytes: file.size,
              upload_timestamp: new Date().toISOString()
            }
          }
        } catch (error) {
          console.error('Error uploading config file:', error)
          this.error = 'Error uploading config file'
        } finally {
          this.uploadingConfigFile = false
        }
      }
      input.click()
    },

    // Test config functionality removed - endpoint not available in new backend


    async uploadPolygonFile(file) {
      this.uploadingPolygon = true
      try {
        const formData = new FormData()
        formData.append('file', file)

        const token = localStorage.getItem('token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}

        const response = await axios.post('/api/upload/polygon', formData, {
          headers: {
            ...headers,
            'Content-Type': 'multipart/form-data'
          }
        })

        if (response.data.success) {
          this.successMessage = 'Polygon data uploaded successfully'
          this.hasUploaded = true
          this.uploadedPolygon = {
            filename: file.name,
            file_size_bytes: file.size,
            upload_timestamp: new Date().toISOString()
          }
        }
      } catch (error) {
        console.error('Error uploading polygon:', error)
        this.error = 'Error uploading polygon data'
      } finally {
        this.uploadingPolygon = false
      }
    },

    async uploadExternalDataFile(file) {
      this.uploadingExternalData = true
      try {
        const formData = new FormData()
        formData.append('file', file)

        const token = localStorage.getItem('token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}

        const response = await axios.post('/api/upload/external-data', formData, {
          headers: {
            ...headers,
            'Content-Type': 'multipart/form-data'
          }
        })

        if (response.data.success) {
          this.successMessage = 'External data uploaded successfully'
          this.hasUploaded = true
          this.uploadedExternalData = {
            filename: file.name,
            file_size_bytes: file.size,
            upload_timestamp: new Date().toISOString()
          }
        }
      } catch (error) {
        console.error('Error uploading external data:', error)
        this.error = 'Error uploading external data'
      } finally {
        this.uploadingExternalData = false
      }
    },

    async uploadConfigFileFile(file) {
      this.uploadingConfigFile = true
      try {
        const formData = new FormData()
        formData.append('file', file)

        const token = localStorage.getItem('token')
        const headers = token ? { Authorization: `Bearer ${token}` } : {}

        const response = await axios.post('/api/upload/config', formData, {
          headers: {
            ...headers,
            'Content-Type': 'multipart/form-data'
          }
        })

        if (response.data.success) {
          this.successMessage = 'Config file uploaded successfully'
          this.hasUploaded = true
          this.uploadedConfigFile = {
            filename: file.name,
            file_size_bytes: file.size,
            upload_timestamp: new Date().toISOString()
          }
        }
      } catch (error) {
        console.error('Error uploading config file:', error)
        this.error = 'Error uploading config file'
      } finally {
        this.uploadingConfigFile = false
      }
    },

    // Test config functionality removed - endpoint not available in new backend

    deletePolygon() {
      this.uploadedPolygon = null
      this.hasUploaded = this.uploadedExternalData || this.uploadedConfigFile
      this.successMessage = 'Polygon file removed'
      setTimeout(() => { this.successMessage = null; }, 3000);
    },

    deleteExternalData() {
      this.uploadedExternalData = null
      this.hasUploaded = this.uploadedPolygon || this.uploadedConfigFile
      this.successMessage = 'External data file removed'
      setTimeout(() => { this.successMessage = null; }, 3000);
    },

    deleteConfigFile() {
      this.uploadedConfigFile = null
      this.hasUploaded = this.uploadedPolygon || this.uploadedExternalData
      this.successMessage = 'Config file removed'
      setTimeout(() => { this.successMessage = null; }, 3000);
    },


    // Utility methods
    getFileIcon(filename) {
      const ext = filename.toLowerCase().split('.').pop();
      switch (ext) {
        case 'csv': return '📊';
        case 'xlsx': case 'xls': return '📈';
        case 'json': case 'geojson': return '📄';
        default: return '📄';
      }
    },
    
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    formatUploadTime(timestamp) {
      return new Date(timestamp).toLocaleString();
    },
    
    showError(message) {
      this.error = message;
      setTimeout(() => { this.error = null; }, 5000);
    },
    
    clearMessagesAfterDelay() {
      setTimeout(() => {
        this.successMessage = null;
        this.error = null;
      }, 5000);
    },
    
    limitActivityHistory() {
      if (this.activityHistory.length > 10) {
        this.activityHistory = this.activityHistory.slice(0, 10);
      }
    }
  }
};
</script>

<style scoped>
.bg-gray-750 {
  background-color: #374151;
}

.animate-progress {
  width: 100%;
  animation: progress 2s ease-in-out infinite;
}

@keyframes progress {
  0% {
    width: 0%;
  }
  50% {
    width: 100%;
  }
  100% {
    width: 0%;
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Custom drag and drop styles */
.border-dashed {
  border-style: dashed;
}
</style>