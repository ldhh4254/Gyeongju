import os
import requests
import pandas as pd
import re
from urllib.parse import unquote, quote

file_name = "gyeongju_cafe_complete.csv"
raw_key = os.environ.get('DATA_GO_KR_KEY', '').strip()
url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

# 공공데이터포털 키 오류를 우회하기 위해 3가지 형태의 키 후보를 준비합니다.
key_candidates = [
    raw_key,                  # 1. 가져온 키 그대로 시도
    unquote(raw_key),         # 2. 디코딩(unquote)된 형태로 변환하여 시도
    quote(raw_key)            # 3. 인코딩(quote)된 형태로 변환하여 시도
]

items = []
success = False

print("📡 공공데이터포털 API 연결을 시작합니다.")

# 3가지 버전의 키를 순서대로 돌려가며 성공할 때까지 API를 찌릅니다.
for idx, key in enumerate(key_candidates, 1):
    if not key:
        continue
    try:
        print(f"🔄 [{idx}차 시도] 인증키 변환 버전 적용 중...")
        params = {'serviceKey': key}
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            # 응답 내용이 올바른 JSON 구조인지 검증
            try:
                response_json = response.json()
                items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
                if items:
                    print(f"🎯 데이터 수집 성공! ({idx}차 키에서 통과)")
                    success = True
                    break
            except Exception:
                # JSON 파싱 실패 시 다음 후보 키로 넘어감
                continue
    except Exception as e:
        print(f"⚠️ 연결 오류 발생: {e}")
        continue

# 데이터 가공 및 저장
if success and items:
    df = pd.DataFrame(items)
    rename_dict = {
        'CON_TITLE': '카페 이름', 'CON_IMM': '주소', 
        'CON_TEL': '전화번호', 'CON_TIME': '운영 및 주차 정보', 
        'CON_CONTENT': '카페 특징 상세'
    }
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    final_df = df[list(available_cols.keys())].rename(columns=available_cols) if available_cols else df.copy()

    for col in final_df.columns:
        final_df[col] = final_df[col].apply(clean_text)
        
    def create_ai_summary(row):
        return f"경주 '{row.get('카페 이름', '카페')}' 정보. 위치: {row.get('주소','없음')}, 연락처: {row.get('전화번호','없음')}. 특징: {row.get('카페 특징 상세','없음')}"

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 대성공! {file_name} 파일에 {len(final_df)}건의 실제 데이터가 저장되었습니다.")
else:
    print("❌ 모든 종류의 키가 거절당했습니다. 깃허브 Secret에 등록된 키 값이 공공데이터포털의 키와 정확히 일치하는지 확인이 필요합니다.")
    # NotebookLM 에러 방지용 최소 기본 틀 유지
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
