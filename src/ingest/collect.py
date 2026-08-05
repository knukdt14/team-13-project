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
    for attempt in range(3):
        res = requests.get(BASE_URL, params=params)
        try:
            data = res.json()
            break
        except requests.exceptions.JSONDecodeError:
            print(f"{page}페이지 응답 파싱 실패 (status={res.status_code}), 재시도 {attempt + 1}/3")
            print(res.text[:300])
            time.sleep(1.5)
    else:
        raise RuntimeError(f"{page}페이지 3회 재시도 실패")

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