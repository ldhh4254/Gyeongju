import requests
import pandas as pd
import os

# 깃허브 환경변수에서 키를 가져오도록 수정됨
service_key = os.getenv('MY_KEY') 

url = 'http://apis.data.go.kr/5050000/cafeInfoService/getCafeInfo'
params = {'serviceKey': service_key, 'pageNo': '1', 'numOfRows': '100', 'type': 'json'}

try:
    response = requests.get(url, params=params)
    items = response.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
    if items:
        df = pd.DataFrame(items)
        final_df = df[['CON_TITLE', 'CON_ADDRESS', 'CON_PHONE', 'CON_SUMMARY', 'CON_CONTENT']].copy()
        final_df.columns = ['카페 이름', '주소', '전화번호', '운영 및 주차 정보', '카페 특징 상세']
        final_df['운영 및 주차 정보'] = final_df['운영 및 주차 정보'].str.replace(r'<[^>]*>|&nbsp;', ' ', regex=True)
        final_df['카페 특징 상세'] = final_df['카페 특징 상세'].str.replace(r'<[^>]*>|&nbsp;', ' ', regex=True)
        # 결과 파일 저장
        final_df.to_csv('gyeongju_cafe_complete.csv', index=False, encoding='utf-8-sig')
        print("✅ 성공!")
except Exception as e:
    print(f"⚠️ 오류: {e}")
