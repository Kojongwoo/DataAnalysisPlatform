# backend/core/views.py

import pandas as pd
import io
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error, r2_score

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.svm import SVC, SVR

# --- 헬퍼 함수 ---
def _analyze_dataframe(df):
    """
    주어진 DataFrame을 분석하여 table, stats, quality JSON을 반환합니다.
    **성능 최적화**: 프론트엔드 렌더링 부하를 줄이기 위해 tableData는 상위 100개 행만 반환합니다.
    """
# --- 1. 전체 테이블 데이터 (Preview용 100개만) ---
    # 💡 전체 데이터를 다 보내면 브라우저가 멈춥니다. 상위 100개만 자릅니다.
    df_preview = df.head(100).copy()
    
    # 💡 [Warning 해결] fillna 대신 where를 사용하여 안전하게 문자열('-')로 변환
    df_preview = df_preview.astype(object).where(pd.notnull(df_preview), '-')
    
    table_json = df_preview.to_json(orient='split', force_ascii=False)

    # --- 2. 기초 통계량 데이터 ---
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
    stats_df = pd.concat([dtype_df, stats_df])
    
    stats_df = stats_df.reset_index()
    stats_df.rename(columns={'index': '구분'}, inplace=True)
    
    # 💡 [Warning 해결] stats_df 처리
    stats_df = stats_df.astype(object).where(pd.notnull(stats_df), '-')
    stats_json = stats_df.to_json(orient='split', force_ascii=False)
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
            
            # 💡 [수정 1] 데이터셋 특화 전처리: '?'를 NaN(결측치)으로 변환
            df.replace('?', np.nan, inplace=True)

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
            # 💡 [수정 2] '?' -> NaN 치환 추가
            df.replace("?", np.nan, inplace=True)

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

class TrainModelView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        df_json = request.data.get('dataframe')
        target_col = request.data.get('target')
        model_name = request.data.get('model_name', 'rf') # 💡 기본값 'rf' (Random Forest)

        if not df_json or not target_col:
            return Response({"error": "데이터 또는 목표 컬럼이 지정되지 않았습니다."}, status=400)

        try:
            # 1. 데이터 복원
            df = pd.read_json(io.StringIO(df_json), orient='split')
            
            # 2. 데이터 전처리 (ID 컬럼 제거 및 결측치 처리)
            cols_to_drop = [c for c in df.columns if 'ID' in c or 'id' in c or 'nbr' in c]
            df_clean = df.drop(columns=cols_to_drop, errors='ignore')

            if target_col in df_clean.columns:
                df_clean = df_clean.dropna(subset=[target_col])
            
            for col in df_clean.columns:
                if df_clean[col].isnull().sum() > 0:
                    # 수치형이면 평균, 아니면 최빈값 (간단한 처리)
                    if pd.api.types.is_numeric_dtype(df_clean[col]):
                        df_clean[col] = df_clean[col].fillna(df_clean[col].mean())
                    else:
                        df_clean[col] = df_clean[col].fillna(df_clean[col].mode()[0])

            if target_col not in df_clean.columns:
                 return Response({"error": f"목표 컬럼 '{target_col}'을 찾을 수 없습니다."}, status=400)

            # 3. 목표 변수(y) 분리 및 타입 판단
            y = df_clean[target_col]
            X = df_clean.drop(columns=[target_col])

            is_regression = False
            if pd.api.types.is_numeric_dtype(y):
                if pd.api.types.is_float_dtype(y) or y.nunique() > 20:
                    is_regression = True

            # 4. 인코딩
            for col in X.select_dtypes(include=['object']).columns:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))

            if not is_regression and y.dtype == 'object':
                le_y = LabelEncoder()
                y = le_y.fit_transform(y.astype(str))

            # 5. 데이터 분리
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

            # 6. 💡 모델 선택 및 학습 (분기 처리)
            model = None
            
            if is_regression:
                # --- 회귀 (Regression) ---
                if model_name == 'linear':
                    model = LinearRegression()
                elif model_name == 'gb':
                    model = GradientBoostingRegressor(n_estimators=100, random_state=42)
                elif model_name == 'svm':
                    model = SVR()
                else: # default 'rf'
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                
                mse = mean_squared_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                result_data = {
                    "type": "regression",
                    "model": model_name,
                    "metrics": {
                        "R2 Score (설명력)": f"{r2:.4f}",
                        "MSE (오차제곱평균)": f"{mse:.4f}"
                    }
                }
            else:
                # --- [CASE 2] 분류 (Classification) ---
                # 💡 핵심: 프론트에서 'linear'라고 보내도, 분류 문제라면 -> LogisticRegression 실행
                if model_name == 'linear' or model_name == 'logistic':
                    model = LogisticRegression(max_iter=1000)
                elif model_name == 'gb':
                    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
                elif model_name == 'svm':
                    model = SVC()
                else: # default 'rf'
                    model = RandomForestClassifier(n_estimators=100, random_state=42)

                # 학습 및 평가
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                
                result_data = {
                    "type": "classification",
                    "model": model_name,
                    "metrics": {
                        "Accuracy (정확도)": f"{accuracy * 100:.2f}%"
                    }
                }

            # 7. 💡 중요 변수 추출 (모델별 속성 차이 처리)
            importances = {}
            
            # (1) 트리 기반 모델 (feature_importances_)
            if hasattr(model, 'feature_importances_'):
                importances = dict(zip(X.columns, model.feature_importances_))
            
            # (2) 선형 모델 (coef_) - 절대값 크기로 중요도 가늠
            elif hasattr(model, 'coef_'):
                # 다중 클래스일 경우 첫 번째 클래스 기준 혹은 평균 사용 등 복잡하지만, 여기선 단순화
                coefs = model.coef_
                if coefs.ndim > 1: 
                    coefs = coefs[0] # 첫 번째 클래스 또는 차원
                importances = dict(zip(X.columns, np.abs(coefs)))
            
            # (3) SVM 등 지원하지 않는 경우 -> 빈 딕셔너리

            if importances:
                sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
                result_data["feature_importances"] = sorted_importances
            else:
                result_data["feature_importances"] = {}


            # 💡 [신규 기능] 결과 해석 및 설명 생성 로직
            explanation = []
            
            # 1. 성능 평가 해석
            if is_regression:
                r2_val = r2 
                if r2_val >= 0.8:
                    grade = "아주 훌륭해요! 🌟"
                    desc = f"AI가 데이터의 패턴을 아주 잘 파악했습니다. (설명력: {r2_val*100:.1f}%)<br>이 모델은 실전에서 사용해도 좋을 만큼 믿음직스럽습니다."
                elif r2_val >= 0.5:
                    grade = "준수합니다. ✅"
                    desc = f"데이터의 흐름을 절반 이상 파악했습니다. (설명력: {r2_val*100:.1f}%)<br>더 많은 데이터를 모으면 성능이 훨씬 좋아질 거예요."
                else:
                    grade = "노력이 필요해요. 😅"
                    desc = f"아직 예측력이 다소 낮습니다. (설명력: {r2_val*100:.1f}%)<br>데이터 전처리를 다시 하거나, 이상치를 제거해 보세요."
                
                explanation.append(f"<strong>[{grade}]</strong> {desc}")
            
            else: # 분류 (Classification)
                acc_val = accuracy * 100
                if acc_val >= 90:
                    grade = "천재적인 수준이에요! 🚀"
                    desc = f"정답률이 {acc_val:.1f}%입니다.<br>거의 모든 케이스를 정확하게 맞추고 있네요!"
                elif acc_val >= 70:
                    grade = "쓸만하네요! 👍"
                    desc = f"정답률이 {acc_val:.1f}%입니다.<br>기본적인 분류는 잘 해내고 있습니다."
                else:
                    grade = "조금 아쉬워요. 🤔"
                    desc = f"정답률이 {acc_val:.1f}%입니다.<br>동전 던지기보다는 낫지만, 개선이 필요해 보입니다."
                
                explanation.append(f"<strong>[{grade}]</strong> {desc}")

            # 2. 중요 변수 해석
            if result_data.get("feature_importances"):
                top_3 = list(result_data["feature_importances"].keys())[:3]
                # 변수 이름들을 강조하기 위해 []로 감싸기
                top_3_str = ", ".join([f"<b>[{f}]</b>" for f in top_3])
                
                insight = f"<br><br>💡 <b>분석 팁</b>: 결과('{target_col}')를 결정짓는 가장 핵심적인 요인은 {top_3_str} 순서입니다."
                insight += f"<br>특히 <b>'{top_3[0]}'</b> 데이터가 변하면 결과도 크게 달라질 가능성이 높으니 주목하세요!"
                explanation.append(insight)
            else:
                explanation.append("<br><br>⚠️ 이 모델은 변수 중요도를 제공하지 않아, 어떤 요인이 중요한지 파악하기 어렵습니다.")

            # 결과 데이터에 설명 추가
            result_data["explanation"] = "".join(explanation)

            # 💡 [신규 기능] 실제값 vs 예측값 비교 샘플 데이터 생성 (최대 10개)
            sample_size = 10
            # 인덱스 리셋을 위해 DataFrame/Series로 변환 보장
            y_test_reset = pd.Series(y_test).reset_index(drop=True)
            y_pred_reset = pd.Series(y_pred).reset_index(drop=True)
            
            samples = []
            
            # (1) 분류 문제일 경우: 라벨 복원 (0, 1 -> 'Yes', 'No')
            if not is_regression and 'le_y' in locals() and le_y is not None:
                # LabelEncoder가 있다면 원래 문자열로 복구
                actual_values = le_y.inverse_transform(y_test_reset[:sample_size].astype(int))
                pred_values = le_y.inverse_transform(y_pred_reset[:sample_size].astype(int))
            else:
                # 회귀거나 인코딩 안 된 경우 그대로 사용
                actual_values = y_test_reset[:sample_size].values
                pred_values = y_pred_reset[:sample_size].values

            # (2) 샘플 리스트 생성
            for i in range(min(len(actual_values), sample_size)):
                actual = actual_values[i]
                pred = pred_values[i]
                
                # 회귀의 경우 소수점 정리
                if is_regression:
                    actual = round(float(actual), 2)
                    pred = round(float(pred), 2)
                    diff = round(abs(actual - pred), 2) # 오차
                    is_correct = diff  # 회귀에서는 오차값 자체
                else:
                    # 분류는 맞음/틀림 여부 (True/False)
                    is_correct = (str(actual) == str(pred))
                
                samples.append({
                    "id": i + 1,
                    "actual": actual,
                    "predicted": pred,
                    "is_correct": is_correct # 분류: bool, 회귀: 오차값(float)
                })

            result_data["samples"] = samples

            return Response(result_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"학습 중 오류 발생: {str(e)}"}, status=500)