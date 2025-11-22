# backend/core/views.py

import pandas as pd
import io
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser

# --- 헬퍼 함수 ---
def _analyze_dataframe(df):
    """
    주어진 DataFrame을 분석하여 table, stats, quality JSON을 반환합니다.
    """
    # 1. 전체 테이블 데이터
    table_json = df.astype(object).fillna('-').to_json(orient='split', force_ascii=False)

    # --- 💡 2. 기초 통계량 데이터 (수정됨) ---
    # (1) 기본 describe 수행
    stats_df = df.describe(include='all')
    
    # (2) 데이터 타입(Data Type) 행 생성
    # 각 컬럼이 수치형인지 아닌지 판별
    dtype_data = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            dtype_data[col] = 'Numeric (수치형)'
        else:
            dtype_data[col] = 'Categorical (범주형)'
            
    # DataFrame으로 변환 (인덱스 이름은 'Data Type')
    dtype_df = pd.DataFrame([dtype_data], index=['Data Type'])
    
    # (3) 기존 통계량 맨 위에 'Data Type' 행 합치기
    stats_df = pd.concat([dtype_df, stats_df])
    
    # (4) 인덱스 초기화 및 JSON 변환 (기존 로직)
    stats_df = stats_df.reset_index() # 'index' 컬럼이 생성됨 (Data Type, count, mean...)
    stats_df.rename(columns={'index': '구분'}, inplace=True) # 보기 좋게 이름 변경
    
    stats_json = stats_df.astype(object).fillna('-').to_json(orient='split', force_ascii=False)
    # --------------------------------------

    # 3. 데이터 품질 데이터
    total_rows = len(df)
    
    missing_counts = df.isnull().sum()

    if total_rows > 0:
        missing_percent = (missing_counts / total_rows * 100).round(2)
    else:
        missing_percent = pd.Series(0.0, index=df.columns)
    
    outlier_counts = pd.Series('-', index=df.columns)
    outlier_percent = pd.Series('-', index=df.columns)
    
    # 수치형 변환 시도 (이상치 계산을 위해)
    # object 타입이라도 숫자로 변환 가능하다면 변환해서 계산
    # 💡 수정: errors='ignore' 대신 coerce로 강제 변환 후 수치형만 선택
    df_numeric = df.copy()
    for col in df_numeric.columns:
        try:
            df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')
        except:
            pass
            
    numeric_cols = df_numeric.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        Q1 = df_numeric[col].quantile(0.25)
        Q3 = df_numeric[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)
        
        count = ((df_numeric[col] < lower_bound) | (df_numeric[col] > upper_bound)).sum()
        outlier_counts[col] = count

        if total_rows > 0:
            outlier_percent[col] = (count / total_rows * 100).round(2)
        else:
            outlier_percent[col] = 0.0
        
    quality_df = pd.DataFrame({
        '결측치 개수': missing_counts,
        '결측치 비율(%)': missing_percent,
        '이상치 개수': outlier_counts,
        '이상치 비율(%)': outlier_percent
    })
    
    quality_df = quality_df.transpose().reset_index()
    quality_df.rename(columns={'index': '구분'}, inplace=True)

    quality_df.replace(np.nan, '-', inplace=True)
    
    # 💡 수정: 경고 방지
    quality_json = quality_df.astype(object).fillna('-').to_json(orient='split', force_ascii=False)

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

            response_data = _analyze_dataframe(df)
            response_data['fullData'] = df.to_json(orient='split', force_ascii=False)
            
            return Response(response_data)

        except Exception as e:
            return Response({"error": f"파일 처리 중 서버 오류 발생: {str(e)}"}, status=500)

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
            
            # 1. 빈 문자열 -> NaN 치환
            df.replace("", np.nan, inplace=True)

            # 2. 수치형 변환 시도
            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except (ValueError, TypeError):
                    pass

            if action == 'drop_na':
                df = df.dropna()
                print(f"결측치 행 제거: {original_rows} -> {len(df)}")
            
            elif action == 'fill_na_mean':
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
                    print(f"수치형 컬럼 평균값 대체 완료: {list(numeric_cols)}")
                # 💡 주의: 문자열 컬럼은 여기서 처리되지 않음

            elif action == 'fill_na_median':
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
                    print(f"수치형 컬럼 중앙값 대체 완료: {list(numeric_cols)}")

            # --- 💡 [신규 추가] 최빈값(Mode)으로 채우기 ---
            elif action == 'fill_na_mode':
                # 모든 컬럼을 순회하며 결측치가 있으면 최빈값으로 채움
                filled_cols = []
                for col in df.columns:
                    if df[col].isnull().sum() > 0:
                        # 최빈값이 여러 개일 수 있으므로 첫 번째([0])를 선택
                        mode_value = df[col].mode()[0]
                        df[col] = df[col].fillna(mode_value)
                        filled_cols.append(col)
                print(f"최빈값 대체 완료 (대상 컬럼): {filled_cols}")

            elif action == 'fill_na_zero':
                df.fillna(0, inplace=True)
                print("모든 컬럼 0으로 대체 완료")

            # --- 💡 [신규 추가] 이상치 처리 로직 ---
            elif action == 'drop_outliers':
                # IQR 방식으로 이상치 식별 후 제거
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                Q1 = df[numeric_cols].quantile(0.25)
                Q3 = df[numeric_cols].quantile(0.75)
                IQR = Q3 - Q1
                
                # 조건: (값 < Lower) 또는 (값 > Upper) 인 데이터가 하나라도 있는 행 제거
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # any(axis=1)은 "각 행에 대해 하나라도 True가 있으면 True"
                outlier_condition = ((df[numeric_cols] < lower_bound) | (df[numeric_cols] > upper_bound)).any(axis=1)
                
                original_rows = len(df)
                df = df[~outlier_condition] # Outlier가 아닌 것만 남김
                print(f"이상치 포함 행 제거: {original_rows} -> {len(df)}")

            elif action == 'cap_outliers':
                # 윈저라이징 (Capping): 이상치를 상한값/하한값으로 대체
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                Q1 = df[numeric_cols].quantile(0.25)
                Q3 = df[numeric_cols].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                for col in numeric_cols:
                    # 하한값보다 작은 값은 하한값으로 치환
                    df[col] = np.where(df[col] < lower_bound[col], lower_bound[col], df[col])
                    # 상한값보다 큰 값은 상한값으로 치환
                    df[col] = np.where(df[col] > upper_bound[col], upper_bound[col], df[col])
                print("이상치 윈저라이징(Capping) 완료")
            
            else:
                return Response({"error": "알 수 없는 작업 요청입니다."}, status=400)

            response_data = _analyze_dataframe(df)
            response_data['fullData'] = df.to_json(orient='split', force_ascii=False)
            
            return Response(response_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"데이터 처리 중 서버 오류 발생: {str(e)}"}, status=500)