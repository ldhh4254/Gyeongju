import os
import re
import requests

# 1. 깃허브 세팅에 등록해주신 API 인증키 이름인 DATA_GO_KR_KEY를 읽어옵니다.
API_KEY = os.environ.get("DATA_GO_KR_KEY")
if API_KEY:
    # 혹시 복사 붙여넣기 중에 따옴표(")나 공백이 들어갔을 경우를 대비해 깔끔하게 정리합니다.
    API_KEY = API_KEY.strip().strip('"').strip("'")

# 2. 저장할 파일 이름을 지정합니다.
OUTPUT_FILE = "gyeongju_places.md"

def clean_html(text):
    """HTML 태그 및 줄바꿈 문자를 깔끔하게 지우거나 다듬어주는 함수입니다."""
    if not text:
        return ""
    # 줄바꿈 태그 변환
    text = text.replace("<br />", "\n").replace("<br>", "\n").replace("&nbsp;", " ")
    # 나머지 HTML 태그들(<p> 등) 제거
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def fetch_api_items(url, service_name):
    """지정된 공공데이터 API 주소에서 데이터를 안전하게 가져옵니다."""
    params = {
        "serviceKey": API_KEY,
        "pageNo": "1",
        "numOfRows": "100",  # 한 번에 최대 100개 상점 정보를 수집합니다.
        "_type": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            # 혹시 한 개만 들어와서 dict 형태인 경우 list로 감싸줍니다.
            if isinstance(items, dict):
                items = [items]
            return items
        elif response.status_code == 403:
            print(f"[경고] {service_name} 권한 오류 (403): 공공데이터포털에서 이 API의 [활용신청]이 완료되었는지 확인해 주세요.")
            return []
        else:
            print(f"[경고] {service_name} 호출 실패 (응답 코드: {response.status_code})")
            return []
    except Exception as e:
        print(f"[오류] {service_name} 통신 중 오류 발생: {e}")
        return []

def fetch_data():
    if not API_KEY:
        print("경고: DATA_GO_KR_KEY 설정이 없습니다. 샘플 데이터를 생성합니다.")
        create_sample_file()
        return

    all_items = []
    seen_titles = set()  # 중복 상점 등록을 방지하기 위한 세트

    # 1) 첫 번째 API: 경주시 메뉴별 음식점 정보
    url_menu = "https://apis.data.go.kr/5050000/menuRstrtService/getMenuRstrt"
    print("1. 메뉴별 음식점 정보 가져오는 중...")
    items_menu = fetch_api_items(url_menu, "메뉴별 음식점 API")
    
    # 2) 두 번째 API: 경주시 먹거리 핫플레이스 정보
    url_hot = "https://apis.data.go.kr/5050000/eatHtpService/getEatHtp"
    print("2. 먹거리 핫플레이스 정보 가져오는 중...")
    items_hot = fetch_api_items(url_hot, "먹거리 핫플레이스 API")

    # 두 데이터 합치기 (중복 상점명은 제거)
    for item in items_menu + items_hot:
        title = clean_html(item.get("CON_TITLE"))
        if title and title not in seen_titles:
            seen_titles.add(title)
            all_items.append(item)

    # 수집된 데이터가 있으면 파일 생성, 없으면 샘플 파일 생성
    if all_items:
        write_markdown_file(all_items)
        print(f"[성공] 총 {len(all_items)}개의 식당/카페 정보를 수집하여 {OUTPUT_FILE} 파일을 업데이트했습니다.")
    else:
        print("\n[알림] 가져온 데이터가 없어 기존 샘플 데이터를 유지합니다.")
        create_sample_file()

def write_markdown_file(items):
    """가져온 데이터를 NotebookLM이 가장 좋아하는 깔끔한 마크다운 문서로 작성합니다."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🌸 경주 맛집 및 카페 정보\n\n")
        f.write("공공데이터포털 경주시 API를 통해 실시간으로 수집된 경주 맛집 및 핫플레이스 목록입니다. NotebookLM이 이해하기 쉽도록 정돈되어 있습니다.\n\n")
        
        for index, item in enumerate(items, 1):
            title = clean_html(item.get("CON_TITLE")) or "이름 없음"
            address = clean_html(item.get("CON_ADDRESS")) or "주소 정보 없음"
            homepage = clean_html(item.get("CON_HOMEPAGE"))
            summary = clean_html(item.get("CON_SUMMARY"))
            content = clean_html(item.get("CON_CONTENT"))
            
            f.write(f"### {index}. {title}\n")
            f.write(f"- 📍 **주소**: {address}\n")
            
            if summary:
                f.write(f"- 📝 **주요 정보 및 메뉴**:\n")
                for line in summary.split("\n"):
                    if line.strip():
                        clean_line = line.strip().lstrip("-").strip()
                        f.write(f"  - {clean_line}\n")
            
            if content and content != summary:
                f.write(f"- 🔍 **상세 설명**: {content}\n")
                
            if homepage:
                f.write(f"- 🔗 **관련 웹사이트**: [{title} 바로가기]({homepage})\n")
                
            f.write("\n---\n\n")

def create_sample_file():
    """API 연동 전이나 키가 작동하지 않을 때 생성되는 샘플 파일입니다."""
    sample_items = [
        {
            "CON_TITLE": "경주 맷돌순두부 (샘플)",
            "CON_ADDRESS": "경상북도 경주시 북군길 9",
            "CON_SUMMARY": "대표메뉴 : 순두부찌개, 파전\n영업시간 : 08:00 - 21:00",
            "CON_CONTENT": "경주 보문단지 근처에서 유명한 맷돌 순두부 전문점입니다."
        },
        {
            "CON_TITLE": "황남아덴 Aden (샘플 카페)",
            "CON_ADDRESS": "경상북도 경주시 첨성로99번길 22",
            "CON_SUMMARY": "대표메뉴 : 아덴커피, 긍정빵\n영업시간 : 10:00 - 22:00",
            "CON_CONTENT": "황리단길에 위치한 아름다운 정원이 있는 한옥 대형 카페입니다."
        }
    ]
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🌸 경주 맛집 및 카페 정보 (샘플 데이터)\n\n")
        f.write("> **안내**: API 연동 과정에서 오류가 있거나 대기 시간일 때 생성되는 예시 데이터입니다.\n\n")
        
        for index, item in enumerate(sample_items, 1):
            f.write(f"### {index}. {item['CON_TITLE']}\n")
            f.write(f"- 📍 **주소**: {item['CON_ADDRESS']}\n")
            f.write(f"- 📝 **주요 정보 및 메뉴**:\n")
            for line in item['CON_SUMMARY'].split("\n"):
                f.write(f"  - {line}\n")
            f.write(f"- 🔍 **상세 설명**: {item['CON_CONTENT']}\n")
            f.write("\n---\n\n")
            
    print(f"테스트용 샘플 데이터를 {OUTPUT_FILE}로 저장했습니다.")

if __name__ == "__main__":
    fetch_data()
