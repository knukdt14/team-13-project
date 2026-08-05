# scripts/fetch_zip_db.py
import sys
import requests
import os
import zipfile
from urllib.parse import unquote
from xml.etree import ElementTree
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
load_dotenv(os.path.join(DATA_DIR, "..", ".env"))

# data.go.kr 발급키는 이미 퍼센트 인코딩된 상태라, requests가 params로 다시 인코딩하면
# 이중 인코딩되어 인증 실패가 남 -> unquote로 원문 복원 후 넘김
API_KEY = unquote(os.environ["EPOST_API_KEY"])
URL = "http://openapi.epost.go.kr/postal/downloadAreaCodeService/downloadAreaCodeService/getAreaCodeInfo"

params = {
    "serviceKey": API_KEY,
    "dwldSe": 1,  # 1:전체DB / 2:변경분DB / 3:범위주소DB / 4:사서함주소DB
}

res = requests.get(URL, params=params)
root = ElementTree.fromstring(res.text)

success_yn = root.findtext(".//successYN")
if success_yn != "Y":
    err_msg = root.findtext(".//errMsg")
    raise RuntimeError(f"우편번호 DB 조회 실패: {err_msg}")

file_url = root.findtext("file")
print(f"다운로드 파일 주소: {file_url}")

zip_path = os.path.join(DATA_DIR, "zipcode_DB.zip")
if os.path.exists(zip_path):
    print(f"zip 이미 존재, 다운로드 스킵: {zip_path}")
else:
    with requests.get(file_url, stream=True) as file_res:
        file_res.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in file_res.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"zip 다운로드 완료: {zip_path}")

extract_dir = os.path.join(DATA_DIR, "zipcode_db")
os.makedirs(extract_dir, exist_ok=True)
with zipfile.ZipFile(zip_path) as zf:
    for info in zf.infolist():
        # 이 zip은 파일명을 cp437이 아니라 cp949로 저장해서, 기본 디코딩 결과가 깨짐 -> 재보정
        name = info.filename.encode("cp437").decode("cp949")
        with zf.open(info) as src, open(os.path.join(extract_dir, name), "wb") as dst:
            dst.write(src.read())

print(f"압축 해제 완료: {extract_dir}")
print("추출된 파일 목록:", os.listdir(extract_dir))
