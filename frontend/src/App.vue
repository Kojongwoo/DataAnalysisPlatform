<template>
  <main>
    <h1>데이터 파일 업로드</h1>
    <input type="file" @change="handleFileUpload">
    
    <div v-if="tableData">
      <h2>분석 결과 (상위 5개)</h2>
      <table>
        <thead>
          <tr>
            <th v-for="column in tableData.columns" :key="column">{{ column }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in tableData.data" :key="index">
            <td v-for="cell in row" :key="cell">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
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
/* 간단한 스타일링 */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
}
th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}
th {
  background-color: #f2f2f2;
}
</style>