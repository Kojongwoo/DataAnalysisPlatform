<template>
  <main>
    <h1>데이터 파일 업로드</h1>
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
          <button @click="handleProcess('drop_na')" :disabled="isLoading">
            결측치가 있는 행 전체 제거
          </button>
          </div>
      </div>
    
    </div> </main>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

// 서버로부터 받은 테이블 데이터를 저장할 변수
const analysisResult = ref(null);
const isLoading = ref(false); // 로딩 상태 추가

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
</script>

<style>
main {
  max-width: 90vw;
  margin: 20px auto;
}

.analysis-layout {
  display: grid;
  /* 1fr 2fr : 통계량 틀이 1, 데이터 틀이 2의 비율로 공간 차지 */
  gap: 20px; /* 두 틀 사이의 간격 */
  margin-top: 20px;
}
/* 로딩 스피너 (간단) */
.loading-spinner {
  margin-top: 20px;
  font-size: 1.2em;
  color: #fbf3f3ff;
}

/* 틀 공통 스타일 */
.table-frame, .stats-frame, .quality-frame {
  border: 1px solid #534f4f; /* 프레임 테두리*/
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
  gap: 10px;
}
.preprocessing-frame button {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 10px 15px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}
.preprocessing-frame button:hover {
  background-color: #0056b3;
}
.preprocessing-frame button:disabled {
  background-color: #555;
  cursor: not-allowed;
}
/* --- 스타일 추가 끝 --- */

/* 테이블 스크롤을 담당하는 컨테이너 */
.table-scroll-container {
  max-height: 800px; /* 틀(프레임) 내부 스크롤 영역의 최대 높이 */
  overflow: auto;    /* 가로 및 세로 스크롤 자동 생성 */
  border: 1px solid #ddd; /* 스크롤 영역 테두리 (선택 사항) */
}

/* .stats-frame .table-scroll-container {
  max-height: 300px; 
} */

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