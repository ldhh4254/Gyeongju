import os
import requests
import pandas as pd
import re
from urllib.parse import unquote, quote

file_name = "gyeongju_cafe_complete.csv"
raw_key = os.environ.get('DATA_GO_KR_KEY', '').strip()

# 🎯 모든 데이터가 온전히 들어있는 오리지널 정상 주소로 복원합니다.
url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    # HTML 태그 제거 및 불필요한 줄바꿈/공백 정제
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ").replace("\r", "").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

key_candidates = [raw_key, unquote(raw_key), quote(raw_key)]
items = []
success = False

print("📡 원본 정상 API 주소로 데이터 수집을 시작합니다.")

for idx, key in enumerate(key_candidates, 1):
    if not key: continue
    try:
        params = {'serviceKey': key}
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            try:
                response_json = response.json()
                # 오리지널 응답 데이터 트리 구조 파싱
                items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                if items and len(items) > 0:
                    success = True
                    break
            except: continue
    except: continue

if success and items:
    df = pd.DataFrame(items)
    
    # 🎯 원본 파일 데이터와 100% 일치하는 Key 매핑
    rename_dict = {
        'CON_TITLE': '카페 이름',
        'CON_IMM': '주소',
        'CON_TEL': '전화번호',
        'CON_TIME': '운영 및 주차 정보',
        'CON_CONTENT': '카페 특징 상세'
    }
    
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    if available_cols:
        final_df = df[list(available_cols.keys())].rename(columns=available_cols)
    else:
        final_df = df.copy()

    # 필수 5대 열 보장 및 데이터 청소
    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # 🤖 NotebookLM이 지식을 완벽하게 흡수할 수 있도록 자연어 문장 컬럼 추가
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 미등록"
        info = f"운영 및 주차 정보: {row['운영 및 주차 정보']}" if row['운영 및 주차 정보'] else ""
        desc = f"상세 소개: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        return f"☕ {name} 안내입니다. {addr}에 있으며, {tel}입니다. {info} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    # 열 순서 정렬 후 저장
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 대성공! 모든 정보가 포함된 {len(final_df)}건의 카페 데이터를 저장했습니다.")
else:
    print("❌ 데이터 수집 실패")
