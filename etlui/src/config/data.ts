import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useForecastConfigStore } from '@/stores/forecastConfig'
import { ICONS } from '@/components/Icons'

const commonIcon = ICONS

export const buildDataImportActions = (deps: {
  loading: { import_gee: boolean; import_pivot_com: boolean; import_pivot_csb: boolean; build_analytics: boolean; calc_csb_alerts: boolean; update_key: boolean; post_forecast: boolean; validate_inputs: boolean }
  results: { import_gee: boolean; import_pivot_com: boolean; import_pivot_csb: boolean; build_analytics: boolean; calc_csb_alerts: boolean; update_key: boolean; post_forecast: boolean; validate_inputs: boolean }
}) => {
  const { loading, results } = deps
  return computed(() => [
    {
      key: 'import_gee',
      label: 'Import GEE',
      icon: commonIcon.download,
      iconClass: 'icon-blue',
      loading: loading.import_gee,
      success: results.import_gee,
      statusText: 'Waiting',
      statusClass: 'status-pending',
      loadingText: 'Processing...',
      successText: '✓ Done'
    },
    {
      key: 'import_pivot_com',
      label: 'Import Pivot COM',
      icon: commonIcon.users,
      iconClass: 'icon-green',
      loading: loading.import_pivot_com,
      success: results.import_pivot_com,
      statusText: 'Waiting',
      statusClass: 'status-pending',
      loadingText: 'Processing...',
      successText: '✓ Done'
    },
    {
      key: 'import_pivot_csb',
      label: 'Import Pivot CSB',
      icon: commonIcon.clipboardList,
      iconClass: 'icon-purple',
      loading: loading.import_pivot_csb,
      success: results.import_pivot_csb,
      statusText: 'Waiting',
      statusClass: 'status-pending',
      loadingText: 'Processing...',
      successText: '✓ Done'
    },
    {
      key: 'build_analytics',
      label: 'Build Analytics',
      icon: commonIcon.chartPie,
      iconClass: 'icon-emerald',
      loading: loading.build_analytics,
      success: results.build_analytics,
      statusText: 'Analytics tables',
      statusClass: 'status-pending',
      loadingText: 'Computing...',
      successText: '✓ Ready'
    }
  ])
}

export const buildPipelineSteps = (deps: {
  configIsValid: boolean
  loadingClimate: boolean
  loadingDisease: boolean
  loadingGeoJSON: boolean
  loadingValidateInputs: boolean
  climateSuccess: boolean
  diseaseSuccess: boolean
  geojsonSuccess: boolean
  validateInputsSuccess: boolean
  forecastReportExists: boolean
  checkForecastReportExists: () => Promise<boolean>
  resetReports: () => Promise<void>
  loading: { post_forecast: boolean; build_analytics: boolean; calc_csb_alerts: boolean; update_key: boolean }
  results: { post_forecast: boolean; build_analytics: boolean; calc_csb_alerts: boolean; update_key: boolean }
}) => {
  const {
    configIsValid,
    loadingClimate,
    loadingDisease,
    loadingGeoJSON,
    loadingValidateInputs,
    climateSuccess,
    diseaseSuccess,
    geojsonSuccess,
    validateInputsSuccess,
    forecastReportExists,
    checkForecastReportExists,
    resetReports,
    loading,
    results
  } = deps

  return computed(() => [
    {
      id: 'step-1',
      title: 'Configuration',
      type: 'custom' as const,
      canProceed: configIsValid
    },
    {
      id: 'step-2',
      title: 'Data Retrieval',
      actions: [
        {
          key: 'fetch_climate',
          label: 'Fetch Climate',
          icon: commonIcon.cloud,
          iconClass: 'icon-sky',
          loading: loadingClimate,
          success: climateSuccess,
          statusText: 'Weather & climate',
          statusClass: 'status-pending',
          loadingText: 'Loading...',
          successText: '✓ Success'
        },
        {
          key: 'fetch_disease',
          label: 'Fetch Disease',
          icon: commonIcon.beaker,
          iconClass: 'icon-teal',
          loading: loadingDisease,
          success: diseaseSuccess,
          statusText: 'Health data',
          statusClass: 'status-pending',
          loadingText: 'Loading...',
          successText: '✓ Success'
        },
        {
          key: 'fetch_geojson',
          label: 'Fetch GeoJSON',
          icon: commonIcon.map,
          iconClass: 'icon-indigo',
          loading: loadingGeoJSON,
          success: geojsonSuccess,
          statusText: 'Geospatial boundaries',
          statusClass: 'status-pending',
          loadingText: 'Loading...',
          successText: '✓ Success'
        },
        {
          key: 'validate_inputs',
          label: 'Validate Inputs',
          icon: commonIcon.checkCircle,
          iconClass: 'icon-teal',
          loading: loadingValidateInputs,
          success: validateInputsSuccess,
          statusText: 'Ready',
          statusClass: 'status-pending',
          loadingText: 'Processing...',
          successText: '✓ Validated'
        }
      ]
    },
    {
      id: 'step-3',
      title: 'Forecast',
      actions: [
        {
          key: 'navigate_to_forecast',
          label: 'Run Forecast',
          subtitle: 'ML forecasting pipeline',
          icon: commonIcon.lightning,
          iconClass: 'icon-orange'
        }
      ]
    },
    {
      id: 'step-4',
      title: 'Approve Forecast',
      actions: [
{
        key: 'view_forecast_report',
        label: 'View Report',
        icon: commonIcon.eye,
        iconClass: 'icon-blue',
        inactive: !forecastReportExists,
        statusText: forecastReportExists ? 'View forecast report' : 'Report unavailable',
        statusClass: forecastReportExists ? 'status-pending' : 'status-inactive'
      }
      ],
      onRefresh: checkForecastReportExists,
      onReset: resetReports
    },
    {
      id: 'step-5',
      title: 'Finalization',
      actions: [
        {
          key: 'post_forecast',
          label: 'Post Forecast',
          icon: commonIcon.upload,
          iconClass: 'icon-rose',
          loading: loading.post_forecast,
          success: results.post_forecast,
          statusText: 'Submit results',
          statusClass: 'status-pending',
          loadingText: 'Publishing...',
          successText: '✓ Published'
        },
        {
          key: 'build_analytics',
          label: 'Build Analytics',
          icon: commonIcon.chartPie,
          iconClass: 'icon-emerald',
          loading: loading.build_analytics,
          success: results.build_analytics,
          statusText: 'Analytics tables',
          statusClass: 'status-pending',
          loadingText: 'Computing...',
          successText: '✓ Ready'
        },
        {
          key: 'calc_csb_alerts',
          label: 'CSB Alerts',
          icon: commonIcon.bell,
          iconClass: 'icon-amber',
          loading: loading.calc_csb_alerts,
          success: results.calc_csb_alerts,
          statusText: 'Alert thresholds',
          statusClass: 'status-pending',
          loadingText: 'Processing...',
          successText: '✓ Done'
        },
        {
          key: 'update_key',
          label: 'Update Key',
          icon: commonIcon.key,
          iconClass: 'icon-slate',
          loading: loading.update_key,
          success: results.update_key,
          statusText: 'API keys',
          statusClass: 'status-pending',
          loadingText: 'Updating...',
          successText: '✓ Updated'
        }
      ]
    }
  ])
}