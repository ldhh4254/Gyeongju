import os
import requests

# 1. 깃허브 세팅에 등록해주신 API 인증키 이름인 DATA_GO_KR_KEY를 읽어옵니다.
API_KEY = os.environ.get("DATA_GO_KR_KEY")

# 2. 저장할 파일 이름을 지정합니다.
OUTPUT_FILE = "gyeongju_places.md"

def fetch_data():
    # 만약 인증키가 설정되어 있지 않다면, 사용자가 테스트해볼 수 있도록 가짜(샘플) 데이터를 만듭니다.
    if not API_KEY:
        print("경고: DATA_GO_KR_KEY 설정이 없습니다. 샘플 데이터를 생성합니다.")
        create_sample_file()
        return

    print("공공데이터포털에서 경주 맛집/카페 정보를 가져오는 중...")
    
    # 한국관광공사의 국문 관광정보 서비스(TourAPI)의 음식점 정보 URL입니다.
    # 경주 지역 코드(areaCode=35)와 음식점 타입(contentTypeId=39)을 사용합니다.
    url = "http://apis.data.go.kr/B551011/KorService1/areaBasedList1"
    
    params = {
        "serviceKey": API_KEY,          # 인증키 (DATA_GO_KR_KEY)
        "numOfRows": "100",             # 가져올 데이터 개수 (최대 100개)
        "pageNo": "1",                  # 첫 번째 페이지
        "MobileOS": "ETC",              # 기기 구분 (기타)
        "MobileApp": "GyeongjuApp",     # 서비스 이름
        "_type": "json",                # 결과 형식을 JSON(글자 기반 데이터)으로 받기
        "listYN": "Y",
        "arrange": "A",                 # 이름 순서로 정렬
        "contentTypeId": "39",          # 39는 음식점/카페 업종을 의미합니다.
        "areaCode": "35"                # 35는 경주 지역 코드입니다.
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # API 호출이 성공했는지 확인합니다.
        if response.status_code != 200:
            print(f"API 호출 실패 (코드: {response.status_code}). 샘플 데이터를 생성합니다.")
            create_sample_file()
            return
            
        data = response.json()
        
        # 응답 데이터에서 실제 맛집 목록이 들어있는 부분을 찾습니다.
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        
        if not items:
            print("가져온 데이터가 없거나 인증키가 아직 활성화되지 않았습니다. 샘플 데이터를 생성합니다.")
            create_sample_file()
            return
            
        # 데이터를 예쁜 마크다운 파일로 작성합니다.
        write_markdown_file(items)
        print(f"성공적으로 데이터를 가져와 {OUTPUT_FILE} 파일을 생성했습니다!")
        
    except Exception as e:
        print(f"에러가 발생했습니다: {e}")
        print("오류 방지를 위해 샘플 데이터를 생성합니다.")
        create_sample_file()

def write_markdown_file(items):
    """API로 가져온 데이터를 예쁜 글(마크다운) 양식으로 바꾸어 파일로 저장합니다."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🌸 경주 맛집 및 카페 정보\n\n")
        f.write("공공데이터포털 API를 통해 주기적으로 자동 업데이트되는 경주 맛집 및 카페 목록입니다.\n\n")
        
        for index, item in enumerate(items, 1):
            title = item.get("title", "이름 없음")
            address = item.get("addr1", "주소 정보 없음")
            tel = item.get("tel", "전화번호 정보 없음")
            image = item.get("firstimage", "") # 맛집 사진 주소
            
            f.write(f"### {index}. {title}\n")
            f.write(f"- 📍 **주소**: {address}\n")
            f.write(f"- 📞 **연락처**: {tel}\n")
            
            # 사진 정보가 있으면 사진도 글에 포함시킵니다.
            if image:
                f.write(f"- 🖼️ **대표 사진**: [사진 보기]({image})\n")
                
            f.write("\n---\n\n")

def create_sample_file():
    """API 키가 없거나 에러가 났을 때 보여줄 샘플(테스트용) 데이터를 생성하는 함수입니다."""
    sample_items = [
        {
            "title": "경주 맷돌순두부 (샘플)",
            "addr1": "경상북도 경주시 북군길 9",
            "tel": "054-775-6877",
            "firstimage": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c"
        },
        {
            "title": "황남아덴 Aden (샘플 카페)",
            "addr1": "경상북도 경주시 첨성로99번길 22",
            "tel": "054-774-2016",
            "firstimage": "https://images.unsplash.com/photo-1509042239860-f550ce710b93"
        },
        {
            "title": "함양집 경주보문점 (샘플)",
            "addr1": "경상북도 경주시 북군길 10-1",
            "tel": "054-777-6900",
            "firstimage": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38"
        }
    ]
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🌸 경주 맛집 및 카페 정보 (샘플 데이터)\n\n")
        f.write("> **안내**: 아직 공공데이터포털 API 인증키(DATA_GO_KR_KEY)가 등록되지 않았거나 작동하지 않아 샘플 데이터를 보여줍니다.\n")
        f.write("> 깃허브 세팅(Settings)에 인증키를 비밀값으로 등록하시면 실시간 실제 데이터로 자동으로 교체됩니다.\n\n")
        
        for index, item in enumerate(sample_items, 1):
            f.write(f"### {index}. {item['title']}\n")
            f.write(f"- 📍 **주소**: {item['addr1']}\n")
            f.write(f"- 📞 **연락처**: {item['tel']}\n")
            f.write(f"- 🖼️ **대표 사진**: [사진 보기]({item['firstimage']})\n")
            f.write("\n---\n\n")
            
    print(f"테스트용 샘플 데이터를 {OUTPUT_FILE}로 저장했습니다.")

if __name__ == "__main__":
    fetch_data()
