import os
import requests
import pandas as pd
import re
from urllib.parse import unquote, quote

file_name = "gyeongju_cafe_complete.csv"
raw_key = os.environ.get('DATA_GO_KR_KEY', '').strip()
# 최신 End Point 주소 유지
url = 'https://apis.data.go.kr/5050000/cafeInfoService/getCafeInfo'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    # HTML 태그 제거 및 공백/특수문자 정제
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ").replace("&lsquo;", "'").replace("&rsquo;", "'")
    return re.sub(r'\s+', ' ', text).strip()

key_candidates = [raw_key, unquote(raw_key), quote(raw_key)]
items = []
success = False

print("📡 공식 명세서 규격 적용하여 경주시 API 호출 시작")

for idx, key in enumerate(key_candidates, 1):
    if not key: continue
    try:
        params = {
            'serviceKey': key,
            'pageNo': '1',
            'numOfRows': '1000' # 전체 데이터를 한 번에 가져오기
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
    
    # 🎯 명세서 스크린샷과 100% 일치하도록 정밀 타격 매핑
    rename_dict = {
        'CON_TITLE': '카페 이름',
        'CON_ADDRESS': '주소',
        'CON_PHONE': '전화번호',
        'CON_TIME': '운영 시간',
        'CON_PARKING': '주차 정보',
        'CON_CONTENT': '카페 특징 상세'
    }
    
    # 존재하는 컬럼 매핑 처리
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    if available_cols:
        final_df = df[list(available_cols.keys())].rename(columns=available_cols)
    else:
        final_df = df.copy()

    # 필수 컬럼 안착 및 텍스트 청소
    required_fields = ['카페 이름', '주소', '전화번호', '운영 시간', '주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # NotebookLM을 위한 맞춤형 자연어 지식 텍스트 생성
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 정보 없음"
        time_info = f"영업시간: {row['운영 시간']}" if row['운영 시간'] else ""
        parking = f"주차 가능 여부: {row['주차 정보']}" if row['주차 정보'] else ""
        desc = f"상세 소개: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        
        return f"☕ {name} 정보입니다. {addr}에 있으며, {tel}입니다. {time_info} {parking} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    # 열 순서 깔끔하게 정렬하여 CSV 저장
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"🎉 대성공! 새로운 명세서 규격으로 총 {len(final_df)}건의 카페 데이터를 채웠습니다.")
else:
    print("❌ 데이터 매핑 실패")
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 시간,주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
