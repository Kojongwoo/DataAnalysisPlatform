# backend/core/views.py

import pandas as pd
import io # <--- Make sure to import this
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser

# --- 헬퍼 함수 (새로 추가) ---
# 데이터프레임을 받아 3종류의 분석 JSON을 반환하는 함수
def _analyze_dataframe(df):
    """
    주어진 DataFrame을 분석하여 table, stats, quality JSON을 반환합니다.
    """
    # 1. 전체 테이블 데이터
    table_json = df.fillna('-').to_json(orient='split', force_ascii=False)

    # 2. 기초 통계량 데이터
    stats_df = df.describe(include='all').reset_index()
    stats_json = stats_df.fillna('-').to_json(orient='split', force_ascii=False)

    # 3. 데이터 품질 데이터
    total_rows = len(df)
    
    missing_counts = df.isnull().sum()

    # --- 💡 수정된 부분 (0으로 나누기 방지) ---
    if total_rows > 0:
        missing_percent = (missing_counts / total_rows * 100).round(2)
    else:
        missing_percent = pd.Series(0.0, index=df.columns)
    # --- 수정 끝 ---
    
    outlier_counts = pd.Series('-', index=df.columns)
    outlier_percent = pd.Series('-', index=df.columns)
    
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)
        
        count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
        outlier_counts[col] = count

        # --- 💡 수정된 부분 (0으로 나누기 방지) ---
        if total_rows > 0:
            outlier_percent[col] = (count / total_rows * 100).round(2)
        else:
            outlier_percent[col] = 0.0
        # --- 수정 끝 ---
        
    quality_df = pd.DataFrame({
        '결측치 개수': missing_counts,
        '결측치 비율(%)': missing_percent,
        '이상치 개수': outlier_counts,
        '이상치 비율(%)': outlier_percent
    })
    
    quality_df = quality_df.transpose().reset_index()
    quality_df.rename(columns={'index': '구분'}, inplace=True)

    quality_df.replace(np.nan, '-', inplace=True)
    
    quality_json = quality_df.fillna('-').to_json(orient='split', force_ascii=False)

    # 4. 3가지 데이터를 딕셔너리에 담아 반환
    return {
        'tableData': table_json,
        'statsData': stats_json,
        'qualityData': quality_json
    }

class FileUploadView(APIView):
    parser_classes = (MultiPartParser,)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "파일이 없습니다."}, status=400)

        try:
            file_buffer = io.BytesIO(file_obj.read())

            if file_obj.name.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_buffer)
            elif file_obj.name.endswith('.csv'):
                try:
                    df = pd.read_csv(file_buffer)
                except UnicodeDecodeError:
                    file_buffer.seek(0)
                    df = pd.read_csv(file_buffer, encoding='cp949')
            else:
                return Response({"error": "지원하지 않는 파일 형식입니다."}, status=400)

            # 💡 1. 세션에 저장하는 코드 (삭제)
            # request.session['dataframe'] = df.to_json(orient='split', force_ascii=False)
            
            # 2. 헬퍼 함수를 호출하여 분석 결과 받기
            response_data = _analyze_dataframe(df)
            
            # 💡 3. 원본 DataFrame(JSON)을 응답에 추가
            response_data['fullData'] = df.to_json(orient='split', force_ascii=False)
            
            return Response(response_data)

        except Exception as e:
            return Response({"error": f"파일 처리 중 서버 오류 발생: {str(e)}"}, status=500)

# --- ProcessDataView (수정) ---
class ProcessDataView(APIView):
    parser_classes = (JSONParser,)
    
    def post(self, request, *args, **kwargs):
        df_json = request.data.get('dataframe')
        action = request.data.get('action')

        if not df_json:
            return Response({"error": "DataFrame이 요청에 포함되지 않았습니다."}, status=400)
        
        try:
            # DataFrame 복원
            df = pd.read_json(io.StringIO(df_json), orient='split')
            original_rows = len(df)
            
            # --- 💡 수정 및 추가된 부분 시작 ---
            if action == 'drop_na':
                df = df.dropna()
                print(f"결측치 행 제거: {original_rows} -> {len(df)}")
            
            elif action == 'fill_na_mean':  # 1. 평균값으로 채우기
                # 수치형 컬럼만 선택
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                # 수치형 컬럼의 결측치를 해당 컬럼의 '평균'으로 채움
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
                print("결측치 평균값 대체 완료")

            elif action == 'fill_na_median': # 2. 중앙값으로 채우기
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                # 수치형 컬럼의 결측치를 해당 컬럼의 '중앙값'으로 채움
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
                print("결측치 중앙값 대체 완료")

            elif action == 'fill_na_zero':   # 3. 0으로 채우기
                # 모든 컬럼의 결측치를 0으로 채움
                df.fillna(0, inplace=True)
                print("결측치 0으로 대체 완료")
            
            else:
                return Response({"error": "알 수 없는 작업 요청입니다."}, status=400)
            # --- 💡 수정 및 추가된 부분 끝 ---

            # 갱신된 분석 결과 생성
            response_data = _analyze_dataframe(df)
            response_data['fullData'] = df.to_json(orient='split', force_ascii=False)
            
            return Response(response_data)

        except Exception as e:
            return Response({"error": f"데이터 처리 중 서버 오류 발생: {str(e)}"}, status=500)