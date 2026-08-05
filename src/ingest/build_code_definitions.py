# scripts/build_code_definitions.py
# API코드정보.xlsx의 "코드정보" 시트를 {필드명: {코드: 코드내용}} 형태로 변환
import json
import os
import openpyxl

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")

# 시트의 필드명이 실제 API 응답 필드명과 대소문자가 다른 경우 보정
FIELD_NAME_FIX = {
    "bizPrdSecd": "bizPrdSeCd",
}

wb = openpyxl.load_workbook(os.path.join(DATA_DIR, "API코드정보.xlsx"), data_only=True)
ws = wb["코드정보"]

code_definitions = {}
current_field = None

for row in ws.iter_rows(min_row=2, values_only=True):
    field, _label, _group, code, content = row
    if field:
        current_field = FIELD_NAME_FIX.get(field, field)
        code_definitions[current_field] = {}
    if current_field and code:
        code_definitions[current_field][code] = content

with open(os.path.join(DATA_DIR, "code_definitions.json"), "w", encoding="utf-8") as f:
    json.dump(code_definitions, f, ensure_ascii=False, indent=2)

print("필드별 코드 수:", {k: len(v) for k, v in code_definitions.items()})
print("data/code_definitions.json 저장 완료")
