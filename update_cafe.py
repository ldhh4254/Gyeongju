import os
import requests
import pandas as pd
import re
from urllib.parse import unquote, quote

file_name = "gyeongju_cafe_complete.csv"
raw_key = os.environ.get('DATA_GO_KR_KEY', '').strip()
url = 'https://apis.data.go.kr/5050000/cafeInfoService/getCafeInfo'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    # HTML 태그 및 공백 정제 (<br />, &gt; 등 제거)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

key_candidates = [raw_key, unquote(raw_key), quote(raw_key)]
items = []
success = False

print("📡 [최신 규격] 경주시 API 데이터 수집을 시작합니다.")

for idx, key in enumerate(key_candidates, 1):
    if not key: continue
    try:
        params = {
            'serviceKey': key,
            'pageNo': '1',
            'numOfRows': '1000'
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            try:
                response_json = response.json()
                body = response_json.get('response', {}).get('body', {})
                items = body.get('items', {})
                if isinstance(items, dict):
                    items = items.get('item', [])
                if items and len(items) > 0:
                    success = True
                    break
            except: continue
    except: continue

if success and items:
    df = pd.DataFrame(items)
    
    # 🎯 경주시 최신 개편 API의 실시간 대소문자 컬럼명을 매핑합니다.
    rename_dict = {
        'conTitle': '카페 이름',
        'conImm': '주소',
        'conTel': '전화번호',
        'conTime': '운영 및 주차 정보',
        'conContent': '카페 특징 상세'
    }
    
    # 존재하는 컬럼만 명확하게 필터링하여 복사 (자동 유추 오류 차단)
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    
    if available_cols:
        final_df = df[list(available_cols.keys())].rename(columns=available_cols)
    else:
        # 혹시 몰라 기존 구버전 대문자 규격도 방어 코드로 유지
        backup_dict = {
            'CON_TITLE': '카페 이름', 'CON_IMM': '주소', 
            'CON_TEL': '전화번호', 'CON_TIME': '운영 및 주차 정보', 
            'CON_CONTENT': '카페 특징 상세'
        }
        available_backup = {k: v for k, v in backup_dict.items() if k in df.columns}
        if available_backup:
            final_df = df[list(available_backup.keys())].rename(columns=available_backup)
        else:
            final_df = df.copy()

    # 5대 필수 컬럼 누락 방지 및 빈 칸 처리
    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # NotebookLM 전용 자연어 서술 요약문 생성
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 미등록"
        time_info = f"운영 시간 정보: {row['운영 및 주차 정보']}" if row['운영 및 주차 정보'] else ""
        desc = f"특징: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        return f"{name} 안내. {addr}, {tel}. {time_info} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    # 컬럼 순서 정렬 및 유효성 확보
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 정밀 교정 완료! 모든 칸이 분리되어 저장되었습니다. (총 {len(final_df)}건)")
else:
    print("❌ 데이터 연동에 실패했습니다.")
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
