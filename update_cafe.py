import os
import requests
import pandas as pd
import re
from urllib.parse import unquote, quote

file_name = "gyeongju_cafe_complete.csv"
raw_key = os.environ.get('DATA_GO_KR_KEY', '').strip()

# [교정] 공공데이터포털 스크린샷에 찍힌 정확한 최신 End Point 주소로 수정합니다.
url = 'https://apis.data.go.kr/5050000/cafeInfoService/getCafeInfo'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

# 인증키 변환 후보군 준비
key_candidates = [
    raw_key,
    unquote(raw_key),
    quote(raw_key)
]

items = []
success = False

print("📡 [새로운 주소] 공공데이터포털 API 연결을 시작합니다.")
print(f"🔗 호출 주소: {url}")

for idx, key in enumerate(key_candidates, 1):
    if not key:
        continue
    try:
        print(f"🔄 [{idx}차 시도] 인증키 적용 중...")
        # 공공데이터포털의 기본 필수 파라미터(페이지 크기 등)를 안전하게 추가합니다.
        params = {
            'serviceKey': key,
            'pageNo': '1',
            'numOfRows': '1000' # 넉넉하게 전체 데이터를 가져오도록 설정
        }
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                # 새 API 구조에 맞춰 안전하게 데이터를 탐색합니다.
                body = response_json.get('response', {}).get('body', {})
                items = body.get('items', {})
                
                # items 내부 구조가 리스트이거나 dict 내부의 item 리스트인 경우를 모두 대응
                if isinstance(items, dict):
                    items = items.get('item', [])
                
                if items and len(items) > 0:
                    print(f"🎯 최신 API 데이터 수집 성공! (총 {len(items)}건 확인)")
                    success = True
                    break
            except Exception as json_err:
                continue
    except Exception as e:
        continue

# 데이터 정제 및 저장
if success and items:
    df = pd.DataFrame(items)
    
    # 공공데이터포털 새 컬럼명 또는 한글 컬럼명 매핑 처리
    # 컬럼명이 바뀌었을 수도 있으므로 존재하는 한글 명칭과 영문 명칭을 유연하게 매핑합니다.
    rename_dict = {
        'CON_TITLE': '카페 이름', 'CON_IMM': '주소', 
        'CON_TEL': '전화번호', 'CON_TIME': '운영 및 주차 정보', 
        'CON_CONTENT': '카페 특징 상세',
        'cafeNm': '카페 이름', 'roadNmAddr': '주소', # 혹시 모를 새 API 영어 컬럼명 대비
        'telNo': '전화번호', 'operTime': '운영 및 주차 정보',
        'dtlContent': '카페 특징 상세'
    }
    
    # 깃허브 기존 뼈대 유지 로직
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    if available_cols:
        final_df = df[list(available_cols.keys())].rename(columns=available_cols)
    else:
        final_df = df.copy()

    # 필수 컬럼 보장
    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""

    # 데이터 청소
    for col in final_df.columns:
        final_df[col] = final_df[col].apply(clean_text)
        
    def create_ai_summary(row):
        return f"경주 '{row.get('카페 이름', '카페')}' 정보. 위치: {row.get('주소','없음')}, 연락처: {row.get('전화번호','없음')}. 특징: {row.get('카페 특징 상세','없음')}"

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    # 최종 필요한 컬럼만 예쁘게 정렬해서 저장
    output_cols = required_fields + ['NotebookLM_참고용_텍스트']
    final_df = final_df[[c for c in output_cols if c in final_df.columns]]
    
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 진짜 대성공! {file_name} 파일에 실제 카페 데이터가 적재되었습니다.")
else:
    print("❌ 새 주소에서도 데이터를 가져오지 못했습니다. API 신청 후 활성화(최대 1~2시간) 대기 중이거나 키 값이 다를 수 있습니다.")
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
