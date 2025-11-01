<template>
  <main>
    <h1>데이터 파일 업로드</h1>
    <input type="file" @change="handleFileUpload">

    <div v-if="isLoading" class="loading-spinner">
      데이터를 분석 중입니다...
    </div>

    <div v-if="analysisResult" class="analysis-layout">
      
      <div class="stats-frame">
        <h2>기초 통계량</h2>
        <div class="table-scroll-container small-table">
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
    

    <div v-if="analysisResult" class="table-frame">
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
      </div> </div> </div> </main>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

// 서버로부터 받은 테이블 데이터를 저장할 변수
const analysisResult = ref(null);
const isLoading = ref(false); // 로딩 상태 추가

const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // FormData 객체를 사용해 파일을 감쌉니다.
  const formData = new FormData();
  formData.append('file', file);

  // 이전에 표시되던 데이터 초기화
  analysisResult.value = null;
  isLoading.value = true; // 로딩 시작

  try {
    // axios를 사용해 Django API 서버로 POST 요청을 보냅니다.
    const response = await axios.post('http://127.0.0.1:8000/api/v1/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    // 백엔드에서 보낸 딕셔너리 데이터를 파싱
    const tableData = JSON.parse(response.data.tableData);
    const statsData = JSON.parse(response.data.statsData);

    // 파싱된 두 데이터를 analysisResult 객체에 저장
    analysisResult.value = {
      tableData: tableData,
      statsData: statsData
    };

    
  } catch (error) {
    console.error('파일 업로드 오류:', error);
    alert('파일을 업로드하는 데 실패했습니다.');
  } finally {
    isLoading.value = false; // 로딩 끝
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
  color: #555;
}

.table-frame, .stats-frame {
  border: 1px solid #534f4f; /* 프레임 테두리*/
  padding: 15px;
  margin-top: 20px;
  background-color: #1d1c1c;
  border-radius: 5px;
  display: flex;
  flex-direction: column;
}

.table-frame h2, .stats-frame h2 {
  margin-bottom: 10px;
}

/* 테이블 스크롤을 담당하는 컨테이너 */
.table-scroll-container {
  max-height: 800px; /* 틀(프레임) 내부 스크롤 영역의 최대 높이 */
  overflow: auto;    /* 가로 및 세로 스크롤 자동 생성 */
  border: 1px solid #ddd; /* 스크롤 영역 테두리 (선택 사항) */
}

/* .stats-frame .table-scroll-container {
  max-height: 300px; 
} */

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