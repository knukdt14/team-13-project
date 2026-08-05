import sys
import requests
import json
import time
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
load_dotenv(os.path.join(DATA_DIR, "..", ".env"))

API_KEY = os.environ["YOUTH_API_KEY"]
BASE_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"

all_policies = []
page = 1
total_count = None

while True:
    params = {
        "apiKeyNm": API_KEY,
        "pageNum": page,
        "pageSize": 100,
        "rtnType": "json"
    }
    # 온통청년 API는 간헐적으로 JSON 대신 오류 HTML을 돌려준다. 파싱에 성공해도
    # result 키가 빠진 응답이 오기도 한다. 둘 다 재시도 대상으로 본다.
    # (전에는 파싱 실패만 재시도해서 1,500건쯤에서 KeyError로 죽었다.)
    data = None
    for attempt in range(5):
        try:
            res = requests.get(BASE_URL, params=params, timeout=30)
            payload = res.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            reason = f"응답 파싱 실패 ({exc.__class__.__name__})"
        else:
            if isinstance(payload.get("result"), dict):
                data = payload
                break
            reason = f"result 키 없음 (keys={list(payload)[:5]})"

        wait = 1.5 * (attempt + 1)          # 서버가 흔들릴 때 몰아치지 않도록
        print(f"{page}페이지 {reason}, {wait:.1f}초 후 재시도 {attempt + 1}/5")
        time.sleep(wait)
    else:
        raise RuntimeError(f"{page}페이지 5회 재시도 실패. 누적 {len(all_policies)}건에서 중단")

    items = data["result"]["youthPolicyList"]
    total_count = data["result"]["pagging"]["totCount"]

    if not items:
        break

    all_policies.extend(items)
    print(f"{page}페이지 수집, 누적 {len(all_policies)}/{total_count}")

    if len(all_policies) >= total_count:
        break

    page += 1
    time.sleep(0.3)

# 저장할 폴더 미리 만들기
os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, "youth_policies_raw.json"), "w", encoding="utf-8") as f:
    json.dump(all_policies, f, ensure_ascii=False, indent=2)

print(f"총 {len(all_policies)}개 정책 수집 완료 → data/youth_policies_raw.json 저장됨")