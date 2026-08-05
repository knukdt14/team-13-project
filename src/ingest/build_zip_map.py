# src/ingest/build_zip_map.py
# 정책 데이터에 실제로 쓰인 우편번호만 골라서 "시도 시군구" 이름으로 매핑
import sys
import os
import csv
import json
import glob

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
ZIPCODE_DB_DIR = os.path.join(DATA_DIR, "zipcode_db")

with open(os.path.join(DATA_DIR, "policies_structured.json"), encoding="utf-8") as f:
    structured = json.load(f)

target_zips = set()
for row in structured:
    target_zips.update(row.get("zipCdList") or [])

print(f"정책 데이터의 고유 우편번호: {len(target_zips)}개")

zip_map = {}
for path in glob.glob(os.path.join(ZIPCODE_DB_DIR, "*.txt")):
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="|")
        header = next(reader)
        zip_idx = header.index("우편번호")
        sido_idx = header.index("시도")
        sigungu_idx = header.index("시군구")

        for row in reader:
            zipcode = row[zip_idx]
            if zipcode in target_zips and zipcode not in zip_map:
                sido, sigungu = row[sido_idx], row[sigungu_idx]
                zip_map[zipcode] = f"{sido} {sigungu}".strip()

    print(f"{os.path.basename(path)} 처리 완료, 누적 매핑 {len(zip_map)}/{len(target_zips)}")
    if len(zip_map) == len(target_zips):
        break  # 다 찾았으면 나머지 파일은 안 열어도 됨

missing = target_zips - zip_map.keys()
if missing:
    print(f"매핑 못 찾은 우편번호 {len(missing)}개: {sorted(missing)[:20]}")

with open(os.path.join(DATA_DIR, "zip_code_map.json"), "w", encoding="utf-8") as f:
    json.dump(zip_map, f, ensure_ascii=False, indent=2)

print(f"data/zip_code_map.json 저장 완료 ({len(zip_map)}개)")
