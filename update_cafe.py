import os
import requests
import pandas as pd
import re

file_name = "gyeongju_cafe_complete.csv"
service_key = os.environ.get('DATA_GO_KR_KEY')
url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'

# 깃허브 액션 환경에서 비밀키가 잘 넘어왔는지 검증
if not service_key:
    print("⚠️ 경고: 깃허브 Secrets에 'DATA_GO_KR_KEY'가 설정되지 않았거나 불러올 수 없습니다.")

params = {'serviceKey': service_key}

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

try:
    print("📡 공공데이터포털 API 호출 시도 중...")
    response = requests.get(url, params=params, timeout=30)
    
    print(f"ℹ️ API 응답 상태 코드: {response.status_code}")
    
    # API가 정상 응답(200)을 주었는지 확인
    if response.status_code == 200:
        try:
            response_json = response.json()
            items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        except Exception as json_err:
            print(f"❌ JSON 파싱 실패 (API 키가 잘못되었거나 서버 에러일 수 있습니다): {json_err}")
            print(f"📄 서버 응답 내용 일부: {response.text[:500]}")
            items = []
            
        if items:
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
            print(f"✅ 데이터 저장 완료: {file_name} (총 {len(final_df)}건)")
        else:
            print("⚠️ 가져온 카페 데이터(item)가 비어 있습니다. API 키를 변환(Encoding <-> Decoding)해볼 필요가 있습니다.")
    else:
        print(f"❌ API 서버 연결 실패. 상태 코드: {response.status_code}")

except Exception as e:
    print(f"⚠️ 실행 중 알 수 없는 오류 발생: {e}")

# [핵심] 데이터 수집 실패 시 깃허브 액션이 128 에러로 팅기지 않도록 빈 파일이라도 생성하여 안전하게 보장합니다.
if not os.path.exists(file_name):
    with open(file_name, 'w', encoding='utf-8-sig') as f:
        f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
    print("🛠️ 안전 장치: 에러 방지를 위해 빈 CSV 파일을 생성했습니다.")
