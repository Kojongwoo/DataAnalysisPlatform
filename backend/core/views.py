# backend/core/views.py

import pandas as pd
import io # <--- Make sure to import this
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser

class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "파일이 없습니다."}, status=400)

        try:
            # Read the file content into an in-memory buffer
            # This makes it easier and safer to read multiple times
            file_buffer = io.BytesIO(file_obj.read())

            if file_obj.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_buffer)
            elif file_obj.name.endswith('.csv'):
                try:
                    # 1st attempt: UTF-8
                    df = pd.read_csv(file_buffer)
                except UnicodeDecodeError:
                    # 2nd attempt: CP949 (for Korean Windows files)
                    file_buffer.seek(0) # IMPORTANT: Go back to the start of the buffer
                    df = pd.read_csv(file_buffer, encoding='cp949')
            else:
                return Response({"error": "지원하지 않는 파일 형식입니다."}, status=400)

            # 1. 전체 테이블 데이터 (JSON 문자열)
            # 결측치를 '-'로 표시 (JSON에서 null 대신)
            table_json = df.fillna('-').to_json(orient='split', force_ascii=False)

            # 2. 기초 통계량 데이터 (JSON 문자열)
            # include='all' : 숫자형, 문자형 컬럼 모두에 대한 통계 생성
            stats_df = df.describe(include='all')
            # 통계량 테이블의 인덱스(count, mean 등)를 리셋하여 컬럼으로 만듦
            stats_df = stats_df.reset_index() 
            stats_json = stats_df.fillna('-').to_json(orient='split', force_ascii=False)

            # 3. 두 데이터를 딕셔너리에 담아 응답
            response_data = {
                'tableData': table_json,
                'statsData': stats_json
            }
            
            return Response(response_data)

        except Exception as e:
            # Return the actual error message for easier debugging
            return Response({"error": f"파일 처리 중 서버 오류 발생: {str(e)}"}, status=500)