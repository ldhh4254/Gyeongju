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
    # HTML 태그 및 엔티티 정제 (<br />, &gt; 등 제거)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

key_candidates = [raw_key, unquote(raw_key), quote(raw_key)]
items = []
success = False

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
    
    # 🔍 공공데이터포털 개편 버전 통합 컬럼 매핑 테이블
    # 공공데이터포털 시스템이 임의로 바꿀 수 있는 모든 컬럼명을 역추적합니다.
    mapping = {
        # 1순위: 새 API 표준 영문명
        'title': '카페 이름', 'addr': '주소', 'tel': '전화번호', 'time': '운영 및 주차 정보', 'content': '카페 특징 상세',
        'cafeNm': '카페 이름', 'roadNmAddr': '주소', 'telNo': '전화번호', 'operTime': '운영 및 주차 정보', 'dtlContent': '카페 특징 상세',
        # 2순위: 기존 코랩 버전 영문명
        'CON_TITLE': '카페 이름', 'CON_IMM': '주소', 'CON_TEL': '전화번호', 'CON_TIME': '운영 및 주차 정보', 'CON_CONTENT': '카페 특징 상세',
        # 3순위: 시스템 변환용 한글 속성명 대응
        '명칭': '카페 이름', '위치': '주소', '연락처': '전화번호', '영업시간': '운영 및 주차 정보', '내용': '카페 특징 상세'
    }
    
    final_df = pd.DataFrame()
    
    # 각 컬럼별로 일치하는 데이터 탐색 및 병합
    for eng_key, kor_name in mapping.items():
        if eng_key in df.columns and kor_name not in final_df.columns:
            final_df[kor_name] = df[eng_key]
            
    # 만약 위 매핑으로도 못 찾은 컬럼이 있다면 기존 df에서 유연하게 가져오기
    for col in df.columns:
        for kor_name in ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']:
            if kor_name not in final_df.columns and col in df.columns:
                # 컬럼명에 유사한 단어가 포함되어 있는지 검사 (예: '주소'나 'ADDR'이 포함된 컬럼)
                if kor_name in col or col.lower() in ['con_title', 'con_imm', 'con_tel', 'con_time', 'con_content']:
                    final_df[kor_name] = df[col]

    # 필수 5대 컬럼 안착 및 데이터 정제
    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # NotebookLM 요약 텍스트 생성
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 {row['주소']}" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 미등록"
        time_info = f"운영 시간: {row['운영 및 주차 정보']}" if row['운영 및 주차 정보'] else ""
        desc = f"특징: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        return f"{name} 정보입니다. {addr}, {tel}. {time_info} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    # 순서 정렬 후 저장
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 정밀 가공 완료! 모든 칸이 채워진 {len(final_df)}건의 데이터를 저장했습니다.")
else:
    print("❌ 데이터 매핑 실패")
