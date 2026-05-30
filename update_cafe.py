import os
import requests
import pandas as pd
import re

file_name = "gyeongju_cafe_complete.csv"
# 깃허브 Secrets에 등록한 인증키를 가져옵니다.
service_key = os.environ.get('DATA_GO_KR_KEY', '').strip()

# 원본 정상 데이터 주소
base_url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ").replace("\r", "").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

if not service_key:
    print("⚠️ 경고: 깃허브 Secrets에 'DATA_GO_KR_KEY'가 설정되지 않았습니다.")

items = []
success = False

try:
    print("📡 인증키 직접 주입 방식으로 경주시 API 호출을 시도합니다.")
    
    # [핵심 교정] requests 내부 인코딩 버그를 피하기 위해 주소창에 인증키를 직접 강제로 결합합니다.
    full_url = f"{base_url}?serviceKey={service_key}"
    
    response = requests.get(full_url, timeout=30)
    print(f"ℹ️ API 응답 상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        # 응답이 정상적인 JSON인지 확인
        try:
            response_json = response.json()
            items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items and len(items) > 0:
                print(f"🎯 데이터 수집 성공! 총 {len(items)}건의 데이터를 가져왔습니다.")
                success = True
        except Exception as json_err:
            print("❌ JSON 파싱 실패: API 키가 잘못되었거나 인코딩이 맞지 않아 서버가 에러 문서(XML)를 보냈을 수 있습니다.")
            print(f"📄 서버 응답 내용 일부: {response.text[:300]}")

except Exception as e:
    print(f"⚠️ 연결 중 오류 발생: {e}")

# 데이터 가공 및 저장
if success and items:
    df = pd.DataFrame(items)
    
    rename_dict = {
        'CON_TITLE': '카페 이름',
        'CON_IMM': '주소',
        'CON_TEL': '전화번호',
        'CON_TIME': '운영 및 주차 정보',
        'CON_CONTENT': '카페 특징 상세'
    }
    
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    final_df = df[list(available_cols.keys())].rename(columns=available_cols) if available_cols else df.copy()

    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 미등록"
        info = f"운영 및 주차 정보: {row['운영 및 주차 정보']}" if row['운영 및 주차 정보'] else ""
        desc = f"상세 소개: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        return f"☕ {name} 안내입니다. {addr}에 있으며, {tel}입니다. {info} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 대성공! 모든 데이터가 포함된 {len(final_df)}건의 파일이 업데이트되었습니다.")
else:
    print("❌ 최종 데이터 적재 실패. 뼈대만 유지합니다.")
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
