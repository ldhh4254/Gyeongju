import os
import requests
import pandas as pd
import re

# 1. 저장 파일명 설정 (깃허브 저장소 루트에 바로 저장)
file_name = "gyeongju_cafe_complete.csv"

# 2. 깃허브 Secrets에서 공공데이터 API 인증키 가져오기
service_key = os.environ.get('DATA_GO_KR_KEY')
url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'
params = {'serviceKey': service_key}

def clean_text(text):
    """NotebookLM의 가독성을 위해 데이터 내 특수문자와 HTML 엔티티를 정제합니다."""
    if pd.isna(text):
        return ""
    text = str(text)
    # HTML 엔티티 정제 (예: &#39; -> ', &quot; -> " 등)
    text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    # 불필요한 연속 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    return text

try:
    # 3. 공공데이터포털 API 호출
    response = requests.get(url, params=params)
    
    # API 응답 구조 파싱 (기존 코랩 데이터 트리 구조 유지)
    response_json = response.json()
    items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
    
    if items:
        # 4. 데이터프레임 생성 및 정제
        df = pd.DataFrame(items)
        
        # 원본 컬럼이 존재할 경우 필터링 및 이름 변경 (기존 스크린샷 기준 매핑)
        # 만약 API 컬럼명이 다를 경우를 대비해 안전하게 처리합니다.
        rename_dict = {
            'CON_TITLE': '카페 이름',
            'CON_IMM': '주소',
            'CON_TEL': '전화번호',
            'CON_TIME': '운영 및 주차 정보',
            'CON_CONTENT': '카페 특징 상세'
        }
        
        # 존재하는 컬럼만 선택하여 이름 변경
        available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
        if available_cols:
            final_df = df[list(available_cols.keys())].rename(columns=available_cols)
        else:
            # 매핑할 컬럼이 없을 경우 한글 컬럼이 이미 존재한다고 판단하고 기존틀 유지
            final_df = df.copy()

        # 모든 텍스트 데이터 정제 처리
        for col in final_df.columns:
            final_df[col] = final_df[col].apply(clean_text)
            
        # 5. [NotebookLM 최적화] AI 학습용 커스텀 요약 문장 컬럼 생성
        # AI가 행(Row) 단위를 단순 표가 아닌 하나의 완성된 정보 스토리로 이해하도록 돕습니다.
        def create_ai_summary(row):
            name = row.get('카페 이름', '이름 모를 카페')
            addr = row.get('주소', '정보 없음')
            tel = row.get('전화번호', '정보 없음')
            info = row.get('운영 및 주차 정보', '정보 없음')
            desc = row.get('카페 특징 상세', '정보 없음')
            
            summary = f"경주에 위치한 '{name}' 카페의 상세 정보입니다. "
            summary += f"위치는 '{addr}'이며, 연락처는 {tel}입니다. "
            if info and info != '정보 없음':
                summary += f"운영 시간 및 주차 정보는 다음과 같습니다: {info}. "
            if desc and desc != '정보 없음':
                summary += f"카페의 주요 특징 및 테마는 다음과 같습니다: {desc}"
            return summary

        final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
        
        # 6. CSV 파일로 저장 (엑셀 및 인코딩 깨짐 방지를 위해 utf-8-sig 사용)
        final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
        print(f"✅ 데이터 수집 및 정제 완료! 파일 저장 경로: {file_name}")
        print(f"📊 총 {len(final_df)}개의 카페 데이터가 업데이트되었습니다.")
        
    else:
        print("❌ 공공데이터 API로부터 수집된 데이터(item)가 없습니다.")

except Exception as e:
    print(f"⚠️ 실행 중 오류가 발생했습니다: {e}")