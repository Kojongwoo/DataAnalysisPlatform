<template>
  <main>
    <h1>데이터 파일 업로드</h1>
    <input type="file" @change="handleFileUpload">

    <div v-if="tableData" class="table-frame">
      <h2>업로드 된 셀</h2>
      <div class="table-scroll-container">
        <table>
          <thead>
            <tr>
              <th v-for="column in tableData.columns" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tableData.data" :key="index">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div> </div> </main>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

// 서버로부터 받은 테이블 데이터를 저장할 변수
const tableData = ref(null);

const handleFileUpload = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // FormData 객체를 사용해 파일을 감쌉니다.
  const formData = new FormData();
  formData.append('file', file);

  try {
    // axios를 사용해 Django API 서버로 POST 요청을 보냅니다.
    const response = await axios.post('http://127.0.0.1:8000/api/v1/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });

    // 응답으로 받은 JSON 문자열을 JavaScript 객체로 파싱합니다.
    tableData.value = JSON.parse(response.data);
    
  } catch (error) {
    console.error('파일 업로드 오류:', error);
    alert('파일을 업로드하는 데 실패했습니다.');
  }
};
</script>

<style>

main {
  max-width: 90vw;
  margin: 20px auto;
}

.table-frame {
  border: 1px solid #534f4f; /* 프레임 테두리*/
  padding: 15px;
  margin-top: 20px;
  background-color: #1d1c1c;
  border-radius: 5px;
}

.table-frame h2 {
  margin-bottom: 10px;
}

/* 테이블 스크롤을 담당하는 컨테이너 */
.table-scroll-container {
  max-height: 800px; /* 틀(프레임) 내부 스크롤 영역의 최대 높이 */
  overflow: auto;    /* 가로 및 세로 스크롤 자동 생성 */
  border: 1px solid #ddd; /* 스크롤 영역 테두리 (선택 사항) */
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