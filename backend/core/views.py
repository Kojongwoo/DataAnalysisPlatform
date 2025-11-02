# backend/core/views.py

import pandas as pd
import io # <--- Make sure to import this
import numpy as np
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

            # 1. 전체 테이블 데이터
            table_json = df.fillna('-').to_json(orient='split', force_ascii=False)

            # 2. 기초 통계량 데이터
            stats_df = df.describe(include='all').reset_index()
            stats_json = stats_df.fillna('-').to_json(orient='split', force_ascii=False)

            # 3. 데이터 품질 데이터 (결측치, 이상치) (NEW)
            total_rows = len(df)
            
            # (A) 결측치 계산
            missing_counts = df.isnull().sum()
            missing_percent = (missing_counts / total_rows * 100).round(2)
            
            # (B) 이상치 계산 (IQR 방식, 숫자형 컬럼에만 적용)
            outlier_counts = pd.Series('-', index=df.columns)
            outlier_percent = pd.Series('-', index=df.columns)
            
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - (1.5 * IQR)
                upper_bound = Q3 + (1.5 * IQR)
                
                # 이상치 개수 계산
                count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                outlier_counts[col] = count
                outlier_percent[col] = (count / total_rows * 100).round(2)
                
            # (C) 품질 데이터프레임 생성
            quality_df = pd.DataFrame({
                '결측치 개수': missing_counts,
                '결측치 비율(%)': missing_percent,
                '이상치 개수': outlier_counts,
                '이상치 비율(%)': outlier_percent
            })
            
            # 행/열 전환 후 'index' 컬럼을 '구분'으로 이름 변경
            quality_df = quality_df.transpose().reset_index()
            quality_df.rename(columns={'index': '구분'}, inplace=True)
            
            quality_json = quality_df.fillna('-').to_json(orient='split', force_ascii=False)


            # 4. 세 가지 데이터를 딕셔너리에 담아 응답
            response_data = {
                'tableData': table_json,
                'statsData': stats_json,
                'qualityData': quality_json # 새로 추가
            }
            
            return Response(response_data)

        except Exception as e:
            # Return the actual error message for easier debugging
            return Response({"error": f"파일 처리 중 서버 오류 발생: {str(e)}"}, status=500)