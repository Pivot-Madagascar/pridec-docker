import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type Disease = 'Malaria' | 'Diarrhea' | 'Respinf'
export type DataSource = 'ADJ' | 'COM' | 'CSB'
export type TestMode = 'OUI' | 'NON'

export interface ForecastConfig {
  disease: Disease | ''
  dataSource: DataSource | ''
  test: TestMode
  forecastStart: string
  alertName: string
  diseaseCode: string
  ouLevel: number | ''
}

const DISEASE_CODE_PREFIX = 'pridec_historic'

const OU_LEVEL_MAP: Record<DataSource, number> = {
  ADJ: 6,
  COM: 6,
  CSB: 5,
}

const ALERT_NAME_MAP: Record<Disease, string> = {
  Malaria: 'CSBMalariaVigilance',
  Diarrhea: 'CSBDiarrheaVigilance',
  Respinf: 'CSBRespinfVigilance',
}

const getForecastStart = (test: TestMode): string => {
  if (test === 'OUI') return '202601'
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  return `${year}${month}`
}

const getDiseaseCode = (disease: Disease, dataSource: DataSource): string => {
  return `${DISEASE_CODE_PREFIX}_${dataSource}${disease}`
}

export const useForecastConfigStore = defineStore('forecastConfig', () => {
  const disease = ref<Disease | ''>('')
  const dataSource = ref<DataSource | ''>('')
  const test = ref<TestMode>('NON')

  const ouLevel = computed(() => {
    if (!dataSource.value) return ''
    return OU_LEVEL_MAP[dataSource.value]
  })

  const forecastStart = computed(() => {
    return getForecastStart(test.value)
  })

  const alertName = computed(() => {
    if (dataSource.value !== 'CSB' || !disease.value) return ''
    return ALERT_NAME_MAP[disease.value]
  })

  const diseaseCode = computed(() => {
    if (!disease.value || !dataSource.value) return ''
    return getDiseaseCode(disease.value, dataSource.value)
  })

  const isValid = computed(() => {
    return disease.value !== '' && dataSource.value !== ''
  })

  const config = computed<ForecastConfig>(() => ({
    disease: disease.value,
    dataSource: dataSource.value,
    test: test.value,
    forecastStart: forecastStart.value,
    alertName: alertName.value,
    diseaseCode: diseaseCode.value,
    ouLevel: ouLevel.value,
  }))

  const setDisease = (value: Disease | '') => {
    disease.value = value
  }

  const setDataSource = (value: DataSource | '') => {
    dataSource.value = value
  }

  const setTest = (value: TestMode) => {
    test.value = value
  }

  const reset = () => {
    disease.value = ''
    dataSource.value = ''
    test.value = 'NON'
  }

  return {
    disease,
    dataSource,
    test,
    ouLevel,
    forecastStart,
    alertName,
    diseaseCode,
    isValid,
    config,
    setDisease,
    setDataSource,
    setTest,
    reset,
  }
})