import os
import requests
import pandas as pd
import re

file_name = "gyeongju_cafe_complete.csv"
service_key = os.environ.get('DATA_GO_KR_KEY', '').strip()
base_url = 'http://apis.data.go.kr/5050000/w_gyeongjucafe/getw_gyeongjucafe'

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text)
    text = re.sub(r'<[^>]*>', ' ', text)
    text = text.replace("&nbsp;", " ").replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace(r"\n", " ").replace("\r", "").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()

def parse_time_from_content(content):
    """본문 서술형 텍스트에서 영업시간 패턴을 강제로 추출합니다."""
    if not content: return ""
    match = re.search(r'(영업시간|운영시간|이용시간)\s*[:=-]?\s*([0-9가-힣시분\s:~.\-~,()]+)', content)
    if match:
        extracted = match.group(0).strip()
        return extracted if len(extracted) < 60 else match.group(1) + " 본문 참고"
    return ""

items = []
success = False

try:
    full_url = f"{base_url}?serviceKey={service_key}"
    response = requests.get(full_url, timeout=30)
    if response.status_code == 200:
        try:
            response_json = response.json()
            items = response_json.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if items and len(items) > 0:
                success = True
        except: pass
except: pass

if success and items:
    df = pd.DataFrame(items)
    
    rename_dict = {
        'CON_TITLE': '카페 이름', 'CON_IMM': '주소', 
        'CON_TEL': '전화번호', 'CON_TIME': '운영 및 주차 정보', 'CON_CONTENT': '카페 특징 상세'
    }
    
    available_cols = {k: v for k, v in rename_dict.items() if k in df.columns}
    final_df = df[list(available_cols.keys())].rename(columns=available_cols) if available_cols else df.copy()

    required_fields = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
    for field in required_fields:
        if field not in final_df.columns:
            final_df[field] = ""
        final_df[field] = final_df[field].apply(clean_text)
        
    # 🎯 [해결 1] 경주시 전산 오류로 인한 중복 데이터(똑같은 카페들)를 완벽하게 제거합니다.
    final_df = final_df.drop_duplicates(subset=['카페 이름'], keep='first')
        
    # 🎯 [해결 2] 비어 있는 운영 및 주차 정보 칸을 본문 텍스트에서 파싱하여 강제로 채웁니다.
    for i, row in final_df.iterrows():
        if not row['운영 및 주차 정보'] or row['운영 및 주차 정보'] == "":
            parsed_time = parse_time_from_content(row['카페 특징 상세'])
            if parsed_time:
                final_df.at[i, '운영 및 주차 정보'] = parsed_time
            elif '주차' in row['카페 특징 상세']:
                final_df.at[i, '운영 및 주차 정보'] = "주차 정보 본문 참고"

    def create_ai_summary(row):
        name = row['카페 이름'] if row['카페 이름'] else '경주 카페'
        addr = f"위치는 '{row['주소']}'" if row['주소'] else "주소 정보 없음"
        tel = f"연락처는 {row['전화번호']}" if row['전화번호'] else "전화번호 미등록"
        info = f"운영/주차 정보: {row['운영 및 주차 정보']}" if row['운영 및 주차 정보'] else ""
        desc = f"상세 소개: {row['카페 특징 상세']}" if row['카페 특징 상세'] else ""
        return f"☕ {name} 안내. {addr}, {tel}. {info} {desc}".strip()

    final_df['NotebookLM_참고용_텍스트'] = final_df.apply(create_ai_summary, axis=1)
    
    final_df = final_df[required_fields + ['NotebookLM_참고용_텍스트']]
    # 인덱스 번호를 깔끔하게 리셋
    final_df.reset_index(drop=True, inplace=True)
    final_df.to_csv(file_name, index=False, encoding='utf-8-sig')
    print(f"✅ 중복 제거 완료! 진짜 알짜배기 데이터 {len(final_df)}건만 최종 적재했습니다.")
else:
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding='utf-8-sig') as f:
            f.write("카페 이름,주소,전화번호,운영 및 주차 정보,카페 특징 상세,NotebookLM_참고용_텍스트\n")
