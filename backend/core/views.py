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

            json_data = df.head().to_json(orient='split', force_ascii=False)
            return Response(json_data)

        except Exception as e:
            # Return the actual error message for easier debugging
            return Response({"error": f"파일 처리 중 서버 오류 발생: {str(e)}"}, status=500)