<template>
  <main>
    <h1>데이터 분석 웹사이트</h1>
    <div>==========================</div>
    <h2>데이터 파일 업로드</h2>
    <input type="file" @change="handleFileUpload">

    <div v-if="isLoading" class="loading-spinner">
      데이터를 분석 중입니다...
    </div>

      <div v-if="analysisResult" class="analysis-layout">
            <div class="table-frame">
        <h2>업로드 된 셀</h2>
        <div class="table-scroll-container">
          <table>
            <thead>
              <tr>
                <th v-for="column in analysisResult.tableData.columns" :key="column">{{ column }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in analysisResult.tableData.data" :key="index">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div> 

      <div class="stats-frame">
        <h2>기초 통계량</h2>
        <div class="table-scroll-container">
          <table>
            <thead>
              <tr>
                <th v-for="column in analysisResult.statsData.columns" :key="column">
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in analysisResult.statsData.data" :key="index">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="analysisResult" class="analysis-layout">
        <div class="chart-frame">
          <DataChart :tableData="analysisResult.tableData" />
        </div>

      </div>

      <div class="quality-frame">
        <h2>데이터 품질 (결측치 / 이상치)</h2>
        <div class="table-scroll-container">
          <table>
            <thead>
              <tr>
                <th v-for="column in analysisResult.qualityData.columns" :key="column">
                  {{ column }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in analysisResult.qualityData.data" :key="index">
                <td v-for="(cell, cellIndex) in row" :key="cellIndex">
                  {{ cell }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="preprocessing-frame">
        <h2>데이터 전처리</h2>
        <p>데이터를 수정/편집합니다. (실행 시 모든 통계와 테이블이 갱신됩니다.)</p>
        
        <div class="button-group">
          <div class="action-section">
            <h3>결측치 처리</h3>
            <button class="btn-danger" @click="handleProcess('drop_na')" :disabled="isLoading">결측치 행 제거</button>
            <button @click="handleProcess('fill_na_mean')" :disabled="isLoading">평균값으로 채우기(숫자형)</button>
            <button @click="handleProcess('fill_na_median')" :disabled="isLoading">중앙값으로 채우기(숫자형)</button>
            <button @click="handleProcess('fill_na_mode')" :disabled="isLoading">최빈값으로 채우기(범주형)</button>
            <button @click="handleProcess('fill_na_zero')" :disabled="isLoading">0으로 채우기</button>
          </div>

          <div class="action-section">
            <h3>이상치 처리</h3>
            <button class="btn-danger" @click="handleProcess('drop_outliers')" :disabled="isLoading">이상치 행 제거</button>
            <button @click="handleProcess('cap_outliers')" :disabled="isLoading">상 / 하한값 대체</button>
          </div>

        </div>
      </div>

      <div class="training-frame">
        <h2>머신러닝 모델 학습 (Prediction)</h2>
        <div class="train-controls">
          <label>예측 목표(Target) 컬럼: </label>
          <select v-model="targetColumn">
            <option v-for="col in analysisResult.tableData.columns" :key="col" :value="col">
              {{ col }}
            </option>
          </select>
          <button class="btn-primary" @click="handleTrain" :disabled="isTraining">
            {{ isTraining ? '학습 중...' : '모델 학습 시작 (Random Forest)' }}
          </button>
        </div>

        <div v-if="trainResult" class="result-box">
          <h3>🎯 학습 결과 ({{ trainResult.type === 'regression' ? '회귀 분석' : '분류 분석' }})</h3>
          
          <div class="metrics-container">
            <p v-for="(value, key) in trainResult.metrics" :key="key" class="metric-item">
              {{ key }}: <strong>{{ value }}</strong>
            </p>
          </div>
          
          <h4>중요 변수 (Feature Importance) Top 5</h4>
          <ul>
            <li v-for="(score, name) in topFeatures" :key="name">
              {{ name }}: {{ (score * 100).toFixed(2) }}%
            </li>
          </ul>
        </div>
      </div>
    </div> 
  </main>
</template>

<script setup>
import { ref, computed } from 'vue';
import axios from 'axios';
import DataChart from './components/DataChart.vue'

// 서버로부터 받은 테이블 데이터를 저장할 변수
const analysisResult = ref(null);
const isLoading = ref(false); // 로딩 상태 추가
const targetColumn = ref('');
const isTraining = ref(false);
const trainResult = ref(null);

// 상위 5개 중요 변수 계산
const topFeatures = computed(() => {
  if (!trainResult.value || !trainResult.value.feature_importances) return {};
  return Object.fromEntries(
    Object.entries(trainResult.value.feature_importances).slice(0, 5)
  );
});

// 💡 1. 서버와 주고받을 원본 DataFrame(JSON 문자열)을 저장할 ref
const fullDataJson = ref(null);

// --- 공통 응답 처리 함수 (새로 추가) ---
// 백엔드가 보낸 3종류의 데이터를 파싱하여 analysisResult에 저장
const updateAnalysisData = (responseData) => {
  const tableData = JSON.parse(responseData.tableData);
  const statsData = JSON.parse(responseData.statsData);
  const qualityData = JSON.parse(responseData.qualityData);

  analysisResult.value = {
    tableData: tableData,
    statsData: statsData,
    qualityData: qualityData
  };
  // 💡 2. 응답받은 원본 데이터를 ref에 저장
  if (responseData.fullData) {
    fullDataJson.value = responseData.fullData;
  }
};

// --- 파일 업로드 핸들러 (수정) ---
const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  analysisResult.value = null;
  isLoading.value = true; 
  fullDataJson.value = null; // 💡 새 파일 업로드 시 초기화

  try {
    const response = await axios.post('http://localhost:8000/api/v1/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      withCredentials: true // 💡 upload에도 추가!
    });
    // 공통 함수를 호출하여 데이터 갱신
    updateAnalysisData(response.data);
    
  } catch (error) {
    console.error('파일 업로드 오류:', error);
    alert('파일을 업로드하는 데 실패했습니다.');
  } finally {
    isLoading.value = false;
  }
};

// --- 전처리 핸들러 (새로 추가) ---
const handleProcess = async (actionName) => {
  if (isLoading.value) return; // 이미 로딩 중이면 중복 실행 방지

  // 💡 3. 전송할 원본 데이터가 없으면 실행 중지
  if (!fullDataJson.value) {
    alert("처리할 원본 데이터가 없습니다. 파일을 다시 업로드해주세요.");
    return;
  }

  isLoading.value = true;
  
  try {
    // 💡 4. 요청 시, 저장해둔 원본 데이터를 'dataframe' 키에 실어 전송
    const response = await axios.post('http://localhost:8000/api/v1/process/', {
      action: actionName,
      dataframe: fullDataJson.value // 💡 <--- 핵심 변경점
    }, {
      withCredentials: true // (이제 세션 안 쓰지만, 그냥 둬도 됩니다)
    });

    // 5. 서버로부터 갱신된 데이터를 받아 화면 전체를 새로고침
    updateAnalysisData(response.data);

  } catch (error) {
    console.error('데이터 처리 오류:', error);
    alert(`데이터 처리에 실패했습니다: ${error.response?.data?.error || error.message}`);
  } finally {
    isLoading.value = false;
  }
};
// 💡 [신규] 학습 요청 핸들러
const handleTrain = async () => {
  if (!fullDataJson.value) return alert("데이터가 없습니다.");
  if (!targetColumn.value) return alert("예측할 목표 컬럼(Target)을 선택해주세요.");

  isTraining.value = true;
  trainResult.value = null;

  try {
    const response = await axios.post('http://localhost:8000/api/v1/train/', {
      dataframe: fullDataJson.value,
      target: targetColumn.value
    });
    
    trainResult.value = response.data;
    alert("모델 학습이 완료되었습니다!");
  } catch (error) {
    console.error(error);
    alert(`학습 실패: ${error.response?.data?.error || error.message}`);
  } finally {
    isTraining.value = false;
  }
};
</script>


<style>
/* 💡 main 태그가 화면 전체를 쓰도록 수정 */
main {
  width: 100%;
  max-width: 100%; /* 90vw 등 제한 제거 */
  margin: 0;
  padding: 0 20px; /* 좌우 여백 살짝 */
}

.analysis-layout {
  display: grid;
  gap: 20px;
  margin-top: 20px;
  width: 100%; /* 레이아웃도 꽉 채우기 */
}
/* 로딩 스피너 */
.loading-spinner {
  margin-top: 20px;
  font-size: 1.2em;
  color: #fbf3f3ff;
}

/* 프레임 스타일 유지 */
.table-frame, .stats-frame, .quality-frame, .chart-frame, .preprocessing-frame {
  border: 1px solid #534f4f;
  padding: 15px;
  margin-top: 20px;
  background-color: #1d1c1c;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
}

.table-frame h2, .stats-frame h2, .quality-frame h2 {
  margin-bottom: 10px;
}

/* --- 전처리 '틀' 스타일 (새로 추가) --- */
.preprocessing-frame p {
  font-size: 0.9em;
  color: #aaa;
  margin-bottom: 15px;
}
.button-group {
  display: flex;
  gap: 20px;
}
.action-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.action-section h3 {
  font-size: 0.9rem;
  color: #888;
  margin-bottom: 5px;
  border-bottom: 1px solid #444;
  padding-bottom: 3px;
}
.preprocessing-frame button {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 14px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.2s;
}
.preprocessing-frame button:hover {
  background-color: #0056b3;
}

/* 💡 학습 프레임 스타일 */
.training-frame {
  grid-column: 1 / -1; /* 전체 너비 */
  border: 1px solid #534f4f;
  padding: 20px;
  background-color: #1d1c1c;
  border-radius: 5px;
  margin-top: 20px;
  color: white;
}

.train-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 20px;
}

.train-controls select {
  padding: 10px;
  border-radius: 5px;
  background: #333;
  color: white;
  border: 1px solid #555;
}

.btn-primary {
  background-color: #28a745; /* 초록색 */
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
}
.btn-primary:hover { background-color: #218838; }
.btn-primary:disabled { background-color: #555; }

.result-box {
  background: #2c2c2c;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #444;
}
.accuracy {
  font-size: 1.2rem;
  color: #42b983; /* Vue Green */
  margin-bottom: 15px;
}
.metric-item {
  font-size: 1.1rem;
  color: #42b983;
  margin-bottom: 5px;
}

/* 제거 버튼은 붉은색 계열로 강조 */
.btn-danger {
  background-color: #dc3545 !important;
}
.btn-danger:hover {
  background-color: #a71d2a !important;
}

.preprocessing-frame button:disabled {
  background-color: #555;
  cursor: not-allowed;
}

/* 테이블 스크롤을 담당하는 컨테이너 */
.table-scroll-container {
  max-height: 800px; /* 틀(프레임) 내부 스크롤 영역의 최대 높이 */
  overflow: auto;    /* 가로 및 세로 스크롤 자동 생성 */
  border: 1px solid #ddd; /* 스크롤 영역 테두리 (선택 사항) */
}

/* '기초 통계량'과 '데이터 품질' 테이블은 스크롤 없이 모두 표시 */
.stats-frame .table-scroll-container,
.quality-frame .table-scroll-container {
  max-height: none; /* 높이 제한 없음 */
  overflow: auto; /* 내용이 넘칠 경우에만 스크롤 (주로 가로 스크롤) */
}

/* 간단한 스타일링 */
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
  white-space: nowrap; /* 셀 내용 줄바꿈 방지 */
  background-color: #7c7c7c; /* 셀 배경색 (테이블이 프레임과 구분되도록) */
}
th {
  background-color: #000000;
  position: sticky;
  top: 0;
  z-index: 1;
}
</style>