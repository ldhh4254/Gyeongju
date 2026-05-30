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
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ").replace("&lsquo;", "'").replace("&rsquo;", "'")
    return re.sub(r'\s+', ' ', text).strip()

def parse_time_from_content(content):
    """경주시 API가 운영시간을 누락했을 때 본문 속 텍스트에서 영업시간 패턴을 추출합니다."""
    if not content: return ""
    # 영업시간, 운영시간, 이용시간 패턴 매칭 (예: 영업시간 : 09:30 ~ 19:00)
    match = re.search(r'(영업시간|운영시간|이용시간)\s*[:=-]?\s*([0-9가-힣시분\s:~.\-~,()]+)', content)
    if match:
        extracted = match.group(0).strip()
        # 너무 길게 잡히는 것 방지 (50자 내외로 끊기)
        return extracted if len(extracted) < 60 else match.group(1) + " 본문 참고"
    return ""

key_candidates = [raw_key, unquote(raw_key), quote(raw_key)]
items = []
success = False

print("📡 공식 명세서 규격 및 본문 텍스트 분석 로직 가동")

for idx, key in enumerate(key_candidates, 1):
    if not key: continue
    try:
        params = {'serviceKey': key, 'pageNo': '1', 'numOfRows': '1000'}
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
    
    rename_dict = {
        'CON_TITLE': '카페 이름',
        'CON_ADDRESS': '주소',
        'CON_PHONE': '전화번호',
        'CON_TIME': '운영 시간',
        'CON_PARKING': '주차 정보',
        'CON_CONTENT': '카페 특징 상세'
    }
    
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    if available_cols:
        final_df = df[list(available_cols.keys())].rename(columns=available_cols)
    else:
        final_df = df.copy()

    required_fields = ['카페 이름', '주소', '전화번호', '운영 시간', '주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # 🎯 [보정 로직] 운영 시간이 비어 있다면 카페 특징 상세 본문에서 글자를 파싱해서 채워 넣습니다.
    for i, row in final_df.iterrows():
        if not row['운영 시간'] or row['운영 시간'] == "":
            parsed_time = parse_time_from_content(row['카페 특징 상세'])
            if parsed_time:
                final_df.at[i, '운영 시간'] = parsed_time
        
        # 주차 정보가 비어있고 본문에 '주차' 단어가 있으면 본문 참고 문구 삽입
        if not row['주차 정보'] or row['주차 정보'] == "":
            if '주차' in row['카페 특징 상세']:
                final_df.at[i, '주차 정보'] = "본문 상세 내용 참고"

    # NotebookLM을 위한 맞춤형 자연어 지식 텍스트 생성
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 정보 없음"
        time_info = f"영업시간 관련: {row['운영 시간']}" if row['운영 시간'] else ""
        parking = f"주차 관련: {row['주차 정보']}" if row['주차 정보'] else ""
        desc = f"상세 소개 내용: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        
        return f"☕ {name} 정보입니다. {addr}에 있으며, {tel}입니다. {time_info} {parking} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"🎉 본문 융합 정밀 가공 완료! 총 {len(final_df)}건 처리.")
else:
    print("❌ 데이터 매핑 실패")
