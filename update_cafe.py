import requests
import pandas as pd
import os

# 깃허브 환경변수에서 키를 가져오도록 설정됨
service_key = os.getenv('MY_KEY')

# [수정] 경주시 카페 정보 서비스 주소로 변경
url = 'http://apis.data.go.kr/6470000/gjCafeInfoService/getGjCafeInfo'
params = {'serviceKey': service_key, 'pageNo': '1', 'numOfRows': '100', 'type': 'json'}

try:
    response = requests.get(url, params=params)
    data = response.json()
    
    # [수정] 경주시 데이터 구조에 맞게 추출 경로 변경
    items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
    
    if items:
        df = pd.DataFrame(items)
        # 결과 파일 저장 (이름은 유지)
        df.to_csv('gyeongju_cafe_complete.csv', index=False, encoding='utf-8-sig')
        print("✅ 성공!")
    else:
        print("❌ 데이터를 찾을 수 없습니다. (인증키나 URL 확인 필요)")
except Exception as e:
    print(f"⚠️ 오류: {e}")
