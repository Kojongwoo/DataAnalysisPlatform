<template>
  <div class="chart-container">
    <div class="chart-header">
      <h3>데이터 분포 시각화 (Histogram)</h3>
      <div class="controls">
        <label>컬럼 선택: </label>
        <select v-model="selectedColumn" @change="updateChart">
          <option v-for="col in numericColumns" :key="col" :value="col">
            {{ col }}
          </option>
        </select>
      </div>
    </div>
    
    <div class="canvas-wrapper" v-if="chartData">
      <Bar :data="chartData" :options="chartOptions" />
    </div>
    <div v-else class="no-data">
      시각화할 수치형 컬럼을 선택해주세요.
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
  CategoryScale,
  LinearScale
} from 'chart.js'
import { Bar } from 'vue-chartjs'

// Chart.js 필수 모듈 등록
ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps({
  tableData: {
    type: Object,
    required: true
  }
})

const selectedColumn = ref('')
const chartData = ref(null)

// 차트 디자인 옵션
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false }, // 히스토그램은 범례 불필요
    tooltip: {
      callbacks: {
        label: (context) => `빈도수: ${context.raw}개`
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: { display: true, text: 'Frequency (빈도)' }
    },
    x: {
      title: { display: true, text: 'Value Range (값 구간)' }
    }
  }
}

// 수치형 컬럼만 필터링 (첫 번째 행 데이터를 보고 판단)
const numericColumns = computed(() => {
  if (!props.tableData || !props.tableData.columns) return []
  
  const columns = props.tableData.columns
  const firstRow = props.tableData.data[0] || []
  
  return columns.filter((col, index) => {
    const val = firstRow[index]
    // 값이 숫자이거나, 숫자로 변환 가능한 문자열인 경우
    return !isNaN(parseFloat(val)) && isFinite(val)
  })
})

// 데이터가 변경되면(전처리 후) 차트도 갱신
watch(() => props.tableData, () => {
  // 현재 선택된 컬럼이 유효하다면 차트 갱신, 아니면 첫번째 수치형 컬럼 선택
  if (numericColumns.value.length > 0) {
    if (!selectedColumn.value || !numericColumns.value.includes(selectedColumn.value)) {
      selectedColumn.value = numericColumns.value[0]
    }
    updateChart()
  }
}, { deep: true })

// 초기 로딩 시 첫번째 컬럼 자동 선택
onMounted(() => {
  if (numericColumns.value.length > 0) {
    selectedColumn.value = numericColumns.value[0]
    updateChart()
  }
})

const updateChart = () => {
  if (!selectedColumn.value) return

  const colIndex = props.tableData.columns.indexOf(selectedColumn.value)
  if (colIndex === -1) return

  // 1. 해당 컬럼의 모든 데이터 추출 (숫자로 변환)
  const rawValues = props.tableData.data
    .map(row => parseFloat(row[colIndex]))
    .filter(val => !isNaN(val)) // NaN 제외

  if (rawValues.length === 0) return

  // 2. 히스토그램 구간(Bin) 계산
  const min = Math.min(...rawValues)
  const max = Math.max(...rawValues)
  const binCount = 15 // 구간 개수 (적절히 조절 가능)
  const step = (max - min) / binCount
  
  const labels = []
  const data = new Array(binCount).fill(0)

  // X축 라벨 생성 (예: "10~20")
  for (let i = 0; i < binCount; i++) {
    const start = min + (step * i)
    const end = min + (step * (i + 1))
    labels.push(`${start.toFixed(1)} ~ ${end.toFixed(1)}`)
  }

  // 데이터 카운팅
  rawValues.forEach(val => {
    let binIndex = Math.floor((val - min) / step)
    if (binIndex >= binCount) binIndex = binCount - 1 // 최대값은 마지막 구간에 포함
    data[binIndex]++
  })

  // 3. 차트 데이터 바인딩
  chartData.value = {
    labels: labels,
    datasets: [
      {
        label: 'Count',
        backgroundColor: 'rgba(54, 162, 235, 0.6)', // 파란색 계열
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
        data: data,
        barPercentage: 1.0, // 히스토그램처럼 막대 붙이기
        categoryPercentage: 1.0
      }
    ]
  }
}
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #444;
}

h3 {
  margin: 0;
  color: #fff;
  font-size: 1.1rem;
}

.controls select {
  padding: 5px 10px;
  border-radius: 4px;
  border: 1px solid #555;
  background-color: #333;
  color: #fff;
}

.canvas-wrapper {
  flex: 1;
  position: relative;
  min-height: 300px;
}

.no-data {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
}
</style>