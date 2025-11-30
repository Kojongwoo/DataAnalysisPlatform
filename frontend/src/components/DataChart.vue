<template>
  <div class="chart-container">
    <div class="chart-header">
      <h3>데이터 시각화 ({{ chartTypeLabel }})</h3>
      
      <div class="controls-row">
        <div class="control-group">
          <label>차트 유형</label>
          <select v-model="chartType" class="form-select">
            <option value="histogram">히스토그램 (분포)</option>
            <option value="scatter">산점도 (관계)</option>
            <option value="line">선 그래프 (추세)</option>
            <option value="pie">파이 차트 (비율)</option>
          </select>
        </div>

        <div class="control-group">
          <label>{{ columnLabel1 }}</label>
          <select v-model="selectedColumn1" class="form-select">
            <option v-for="col in availableColumns1" :key="col" :value="col">
              {{ col }}
            </option>
          </select>
        </div>

        <div class="control-group" v-if="chartType === 'scatter'">
          <label>Y축 컬럼 (Target)</label>
          <select v-model="selectedColumn2" class="form-select">
            <option v-for="col in numericColumns" :key="col" :value="col">
              {{ col }}
            </option>
          </select>
        </div>
      </div>
    </div>
    
    <div class="canvas-wrapper" v-if="chartData">
      <component 
        :is="chartComponent" 
        :data="chartData" 
        :options="chartOptions" 
      />
    </div>
    <div v-else class="no-data">
      데이터를 시각화할 컬럼을 선택해주세요.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale
} from 'chart.js'
import { Bar, Line, Scatter, Pie } from 'vue-chartjs'

// Chart.js 모듈 등록 (다양한 차트를 위해 필수 요소 추가)
ChartJS.register(
  CategoryScale, 
  LinearScale, 
  BarElement, 
  LineElement, 
  PointElement, 
  ArcElement,
  Title, 
  Tooltip, 
  Legend
)

const props = defineProps({
  tableData: {
    type: Object,
    required: true
  }
})

// --- 상태 변수 ---
const chartType = ref('histogram')
const selectedColumn1 = ref('')
const selectedColumn2 = ref('')
const chartData = ref(null)

// --- Computed Properties ---

// 1. 수치형 컬럼 필터링
const numericColumns = computed(() => {
  if (!props.tableData || !props.tableData.columns) return []
  const columns = props.tableData.columns
  const firstRow = props.tableData.data[0] || []
  
  return columns.filter((col, index) => {
    const val = firstRow[index]
    return !isNaN(parseFloat(val)) && isFinite(val)
  })
})

// 2. 모든 컬럼 (파이 차트용)
const allColumns = computed(() => {
  return props.tableData?.columns || []
})

const availableColumns1 = computed(() => {
  // 범주형 차트(막대, 파이)는 모든 컬럼 허용 (문자열 포함)
  if (chartType.value === 'bar-categorical' || chartType.value === 'pie') {
    return allColumns.value
  }
  // 수치형 차트(히스토그램, 산점도, 선)는 수치형만 허용
  return numericColumns.value
})

const chartComponent = computed(() => {
  switch (chartType.value) {
    case 'histogram': return Bar
    case 'bar-categorical': return Bar // 💡 막대 그래프 컴포넌트 재사용
    case 'scatter': return Scatter
    case 'line': return Line
    case 'pie': return Pie
    default: return Bar
  }
})

const chartTypeLabel = computed(() => {
  const map = {
    histogram: 'Histogram',
    'bar-categorical': 'Bar Chart (Count)',
    scatter: 'Scatter Plot',
    line: 'Line Chart',
    pie: 'Pie Chart'
  }
  return map[chartType.value]
})

const columnLabel1 = computed(() => {
  if (chartType.value === 'scatter') return 'X축 컬럼'
  if (chartType.value === 'bar-categorical' || chartType.value === 'pie') return '범주(Category) 컬럼'
  return '대상 컬럼'
})

// --- Watchers ---
// 데이터가 변경되면 초기화
watch(() => props.tableData, () => {
  initSelection()
}, { deep: true })

// 차트 타입이나 컬럼이 바뀌면 차트 갱신
watch([chartType, selectedColumn1, selectedColumn2], () => {
  updateChart()
})

// --- Methods ---
const initSelection = () => {
  if (numericColumns.value.length > 0) {
    selectedColumn1.value = numericColumns.value[0]
    if (numericColumns.value.length > 1) {
      selectedColumn2.value = numericColumns.value[1]
    } else {
      selectedColumn2.value = numericColumns.value[0]
    }
  }
  updateChart()
}

const getColumnIndex = (colName) => props.tableData.columns.indexOf(colName)

const getColumnData = (colName) => {
  const idx = getColumnIndex(colName)
  if (idx === -1) return []
  return props.tableData.data.map(row => row[idx])
}

// 차트 그리기 로직 (핵심)
const updateChart = () => {
  if (!selectedColumn1.value) return
  
  // 1. 히스토그램 (기존 로직 유지)
  if (chartType.value === 'histogram') {
    generateHistogram()
  } 
  // 범주형 데이터
  else if (chartType.value === 'bar-categorical') generateBarCategoricalChart()
  // 2. 산점도 (Scatter)
  else if (chartType.value === 'scatter') {
    generateScatter()
  } 
  // 3. 선 그래프 (Line)
  else if (chartType.value === 'line') {
    generateLineChart()
  } 
  // 4. 파이 차트 (Pie)
  else if (chartType.value === 'pie') {
    generatePieChart()
  }
}

// --- 개별 차트 생성 함수들 ---

const generateHistogram = () => {
  const rawValues = getColumnData(selectedColumn1.value)
    .map(v => parseFloat(v)).filter(v => !isNaN(v))
  
  if (rawValues.length === 0) return

  const min = Math.min(...rawValues)
  const max = Math.max(...rawValues)
  const binCount = 15
  const step = (max - min) / binCount
  
  const labels = []
  const data = new Array(binCount).fill(0)

  for (let i = 0; i < binCount; i++) {
    const start = min + (step * i)
    const end = min + (step * (i + 1))
    labels.push(`${start.toFixed(1)}~${end.toFixed(1)}`)
  }

  rawValues.forEach(val => {
    let idx = Math.floor((val - min) / step)
    if (idx >= binCount) idx = binCount - 1
    data[idx]++
  })

  chartData.value = {
    labels,
    datasets: [{
      label: selectedColumn1.value,
      backgroundColor: '#42b983',
      data: data,
      barPercentage: 1.0,
      categoryPercentage: 1.0
    }]
  }
}

// 💡 [신규] 범주형 막대 그래프 생성 함수
const generateBarCategoricalChart = () => {
  const rawValues = getColumnData(selectedColumn1.value)
  
  // 빈도수 계산 (Value Counts)
  const counts = {}
  rawValues.forEach(val => {
    const key = String(val) // 문자열로 통일
    counts[key] = (counts[key] || 0) + 1
  })

  // 빈도수 내림차순 정렬 후 상위 20개만 표시 (너무 많으면 보기 힘듦)
  const sortedEntries = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)

  chartData.value = {
    labels: sortedEntries.map(e => e[0]), // X축: 범주 이름
    datasets: [{
      label: '빈도수 (Count)',
      backgroundColor: '#36a2eb',
      data: sortedEntries.map(e => e[1]) // Y축: 개수
    }]
  }
}

const generateScatter = () => {
  if (!selectedColumn2.value) return

  const xValues = getColumnData(selectedColumn1.value)
  const yValues = getColumnData(selectedColumn2.value)

  // {x: 1, y: 2} 형태의 데이터 생성
  const dataPoints = xValues.map((x, i) => ({
    x: parseFloat(x),
    y: parseFloat(yValues[i])
  })).filter(p => !isNaN(p.x) && !isNaN(p.y))

  // 데이터가 너무 많으면 1000개로 샘플링 (성능 최적화)
  const finalData = dataPoints.length > 1000 
    ? dataPoints.slice(0, 1000) 
    : dataPoints

  chartData.value = {
    datasets: [{
      label: `${selectedColumn1.value} vs ${selectedColumn2.value}`,
      backgroundColor: '#ff6384',
      data: finalData
    }]
  }
}

const generateLineChart = () => {
  const rawValues = getColumnData(selectedColumn1.value)
    .map(v => parseFloat(v)).filter(v => !isNaN(v))
  
  // 데이터가 너무 많으면 앞부분 100개만 표시 (예시)
  const limit = 100
  const displayData = rawValues.slice(0, limit)
  const labels = Array.from({length: displayData.length}, (_, i) => i + 1)

  chartData.value = {
    labels,
    datasets: [{
      label: selectedColumn1.value,
      borderColor: '#36a2eb',
      backgroundColor: 'rgba(54, 162, 235, 0.2)',
      data: displayData,
      tension: 0.1,
      fill: true
    }]
  }
}

const generatePieChart = () => {
  const rawValues = getColumnData(selectedColumn1.value)
  const counts = {}
  rawValues.forEach(val => {
    const key = String(val)
    counts[key] = (counts[key] || 0) + 1
  })

  // 빈도수 상위 10개 추출
  const sortedEntries = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)

  const labels = sortedEntries.map(e => e[0])
  const data = sortedEntries.map(e => e[1])

  // 💡 [수정] 랜덤 대신 '균등 분할' 방식 적용
  // 데이터 개수(labels.length)만큼 360도 색상환을 쪼개서 배정합니다.
  const colors = labels.map((_, i) => {
    // 예: 10개라면 0도, 36도, 72도... 순서로 배정되어 겹치지 않음
    const hue = (i * 360) / labels.length 
    return `hsl(${hue}, 70%, 50%)`
  })

  chartData.value = {
    labels,
    datasets: [{
      backgroundColor: colors,
      data: data
    }]
  }
}

// 차트 옵션 (공통 및 타입별 미세 조정 가능)
const chartOptions = computed(() => {
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: chartType.value !== 'histogram' }, // 히스토그램만 범례 숨김
    }
  }

  if (chartType.value === 'scatter') {
    options.scales = {
      x: { 
        type: 'linear', 
        position: 'bottom',
        title: { display: true, text: selectedColumn1.value }
      },
      y: { 
        title: { display: true, text: selectedColumn2.value } 
      }
    }
  }
  // 💡 막대 그래프 축 제목 추가
  else if (chartType.value === 'bar-categorical') {
    options.scales = {
      x: { title: { display: true, text: 'Categories' } },
      y: { title: { display: true, text: 'Count' } }
    }
  }
  
  return options
})

onMounted(() => {
  initSelection()
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 450px; /* 높이 약간 증가 */
  display: flex;
  flex-direction: column;
}

.chart-header {
  margin-bottom: 15px;
  border-bottom: 1px solid #444;
  padding-bottom: 15px;
}

.chart-header h3 {
  margin: 0 0 15px 0;
  color: #fff;
  font-size: 1.2rem;
}

.controls-row {
  display: flex;
  gap: 15px;
  flex-wrap: wrap; /* 화면 작을 때 줄바꿈 */
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.control-group label {
  font-size: 0.85rem;
  color: #aaa;
}

.form-select {
  padding: 6px 10px;
  border-radius: 4px;
  border: 1px solid #555;
  background-color: #333;
  color: #fff;
  min-width: 150px;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  min-height: 350px;
  background-color: #232323; /* 차트 배경을 살짝 밝게 */
  border-radius: 8px;
  padding: 10px;
}

.no-data {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}
</style>