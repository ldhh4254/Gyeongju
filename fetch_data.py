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

def fetch_data():
    if not API_KEY:
        print("경고: DATA_GO_KR_KEY 설정이 없습니다. 샘플 데이터를 생성합니다.")
        create_sample_file()
        return

    print("공공데이터포털에서 경주 맛집 정보를 가져오는 중...")
    
    # 사용자님의 인증키가 활성화된 경주시 메뉴별음식점 API 엔드포인트입니다.
    url = "https://apis.data.go.kr/5050000/menuRstrtService/getMenuRstrt"
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
            
            if items:
                write_markdown_file(items)
                print(f"성공! 경주시 메뉴별음식점 API에서 데이터를 가져와 {OUTPUT_FILE} 파일을 생성했습니다.")
                return
            else:
                print("응답은 성공했으나 데이터 내용이 비어있습니다. 샘플 데이터를 생성합니다.")
                create_sample_file()
        else:
            print(f"API 호출 실패 (코드: {response.status_code}). 샘플 데이터를 생성합니다.")
            create_sample_file()
            
    except Exception as e:
        print(f"오류 발생: {e}. 샘플 데이터를 생성합니다.")
        create_sample_file()

def write_markdown_file(items):
    """가져온 데이터를 NotebookLM이 가장 좋아하는 깔끔한 마크다운 문서로 작성합니다."""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 🌸 경주 맛집 및 카페 정보\n\n")
        f.write("공공데이터포털 경주시 API를 통해 실시간으로 수집된 경주 맛집 목록입니다. NotebookLM이 이해하기 쉽도록 정돈되어 있습니다.\n\n")
        
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
                # 정보를 줄바꿈 단위로 쪼개어 보기 좋게 정렬합니다.
                for line in summary.split("\n"):
                    if line.strip():
                        # 불필요한 기호 제거 및 보기 좋게 포맷팅
                        clean_line = line.strip().lstrip("-").strip()
                        f.write(f"  - {clean_line}\n")
            
            # 긴 소개글이 있고, 그것이 요약본과 다를 때만 출력합니다.
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
