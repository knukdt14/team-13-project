import json
import os
import html
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 읽기
with open(os.path.join(DATA_DIR, "youth_policies_raw.json"), encoding="utf-8") as f:
    all_policies = json.load(f)

with open(os.path.join(DATA_DIR, "code_definitions.json"), encoding="utf-8") as f:
    CODE_DEFS = json.load(f)

FILTER_FIELDS = [
    "plcyNo", "plcyNm", "plcyKywdNm", "lclsfNm", "mclsfNm",
    # 서술형 본문. 예전에는 rag_docs 에만 담고 여기서는 버렸는데, 그 탓에
    # 백엔드가 읽는 policies_structured.json 에 본문이 하나도 없었다.
    #   - 정책 카드의 summary 가 2,698건 전부 빈 문자열
    #   - 목록 검색이 제목·키워드만 훑음 ("월세"가 11건만 나옴)
    #   - 후속 질문용 policy_to_generator_payload 가 빈 본문을 LLM 에 넘김
    #   - 제출서류를 화면에 보여줄 수 없음 (실제 서류명이 적힌 정책 506건)
    "plcyExplnCn", "plcySprtCn", "plcyAplyMthdCn",
    "sbmsnDcmntCn", "addAplyQlfcCndCn", "ptcpPrpTrgtCn",
    "sprtTrgtMinAge", "sprtTrgtMaxAge", "sprtTrgtAgeLmtYn",
    "mrgSttsCd", "earnCndSeCd", "earnMinAmt", "earnMaxAmt", "earnEtcCn",
    "zipCd", "sbizCd", "jobCd", "schoolCd", "plcyMajorCd",
    "aplyYmd", "aplyPrdSeCd", "bizPrdSeCd", "bizPrdBgngYmd", "bizPrdEndYmd", "bizPrdEtcCn",
    "pvsnInstGroupCd", "plcyPvsnMthdCd", "plcyAprvSttsCd",
    "sprvsnInstCd", "sprvsnInstCdNm", "sprvsnInstPicNm",
    "operInstCd", "operInstCdNm", "operInstPicNm",
    "rgtrInstCd", "rgtrInstCdNm", "rgtrUpInstCd", "rgtrUpInstCdNm",
    "rgtrHghrkInstCd", "rgtrHghrkInstCdNm",
    "sprtSclLmtYn", "sprtSclCnt", "sprtArvlSeqYn",
    "aplyUrlAddr", "refUrlAddr1", "refUrlAddr2",
    "inqCnt", "frstRegDt", "lastMdfcnDt",
]

# 단일 코드값 필드 -> 디코딩된 이름 필드로 추가
SINGLE_CODE_FIELDS = ["mrgSttsCd", "earnCndSeCd", "aplyPrdSeCd", "bizPrdSeCd",
                       "pvsnInstGroupCd", "plcyPvsnMthdCd", "plcyAprvSttsCd"]
# 콤마로 여러 값이 들어올 수 있는 코드값 필드 -> 리스트로 쪼개고 디코딩
MULTI_CODE_FIELDS = ["sbizCd", "jobCd", "schoolCd", "plcyMajorCd"]

# 관공서 문서 특유의 장식용 불릿/기호 (RAG 임베딩에 노이즈만 됨)
DECORATIVE_CHARS = "○❍ㅇ▶▷▪◦□✿☞▸✔✓★☆◎‧․ㆍ※‣▴•*'\"‘’“”"
CIRCLED_NUMBERS = {ch: f"{i}." for i, ch in enumerate("①②③④⑤⑥⑦⑧⑨⑩", start=1)}
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # 이모지
    "\U00002600-\U000027BF"  # 기타 심볼/딩뱃
    "\U0001F000-\U0001F0FF"
    "\U00002190-\U000021FF"  # 화살표
    "\U0000E000-\U0000F8FF"  # 사설 영역(PUA) - 워드/한글 문서에서 깨져 들어온 글리프
    "]+"
)


def unescape_html(text):
    # 원본이 이중 인코딩된 경우가 있어서(&amp;bull; 등) 변화가 없을 때까지 반복 해제
    prev = None
    while prev != text:
        prev = text
        text = html.unescape(text)
    return text


# "값 없음"을 뜻하는 플레이스홀더 (실제 정보인 "별도 문의"/"공고문 참조" 등은 포함하지 않음)
EMPTY_PLACEHOLDERS = {"-", "--", "해당없음", "해당 없음", "제한없음", "제한 없음", "."}


def clean_text(text):
    if not text:
        return ""
    if text.strip() in EMPTY_PLACEHOLDERS:
        return ""
    text = unescape_html(text)
    for ch, num in CIRCLED_NUMBERS.items():
        text = text.replace(ch, num)    # ①②③ -> 1. 2. 3. (순서 정보는 유지)
    text = EMOJI_PATTERN.sub("", text)  # 이모지, 화살표, 깨진 글리프 제거
    text = text.replace("/*", " ")      # 원문 주석 표기(/* ...) 제거
    text = text.translate({ord(ch): None for ch in DECORATIVE_CHARS})  # 장식 기호 제거 (별표 포함)
    text = re.sub(r'\s+[-·]\s+', '. ', text)  # 줄바꿈 제거로 뭉개진 리스트 항목 구분자 -> 문장 구분
    text = re.sub(r':\s*\.\s*', ': ', text)   # '라벨: .' 같은 어색한 잔재 정리
    text = re.sub(r'\.{2,}', '.', text)       # 중복 마침표 정리
    text = re.sub(r'\s+', ' ', text)    # 연속 공백 정리
    return text.strip()


def clean_field(value):
    if value is None:
        return None
    v = unescape_html(value.strip())
    if not v or v in EMPTY_PLACEHOLDERS:
        return None                     # 공백이거나 '-' 같은 플레이스홀더면 None으로
    return v


def decode_code(field, code):
    return CODE_DEFS.get(field, {}).get(code, code)


# 코드/URL/날짜성 필드가 아니라 자유서술형 텍스트라 clean_text()로 장식기호까지 정리해야 하는 필드
# 관공서 원문에는 ○ ▶ ※ 같은 장식 불릿과 이모지가 섞여 있다. 그대로 두면
# 카드에 그 기호가 노출되고 LLM 입력에도 노이즈로 들어간다.
FREE_TEXT_FIELDS = {
    "bizPrdEtcCn", "earnEtcCn",
    "plcyExplnCn", "plcySprtCn", "plcyAplyMthdCn",
    "sbmsnDcmntCn", "addAplyQlfcCndCn", "ptcpPrpTrgtCn",
}


def clean_structured_field(field, value):
    if value is None:
        return None
    if field in FREE_TEXT_FIELDS:
        cleaned = clean_text(value)
        return cleaned if cleaned else None
    return clean_field(value)


def parse_aply_ymd(value):
    # "20260723 ~ 20260806" -> {aplyStartYmd, aplyEndYmd, aplyPeriods}
    # 드물게 "\N"으로 여러 기간이 붙는 경우(연간 반복 등)도 있어서 전부 파싱
    if not value:
        return {"aplyStartYmd": None, "aplyEndYmd": None, "aplyPeriods": []}

    periods = []
    for chunk in value.split("\\N"):
        m = re.match(r"^(\d{8})\s*~\s*(\d{8})$", chunk.strip())
        if not m:
            continue
        start, end = m.groups()
        periods.append({
            "start": f"{start[:4]}-{start[4:6]}-{start[6:]}",
            "end": f"{end[:4]}-{end[4:6]}-{end[6:]}",
        })

    if not periods:
        return {"aplyStartYmd": None, "aplyEndYmd": None, "aplyPeriods": []}

    return {
        "aplyStartYmd": min(p["start"] for p in periods),
        "aplyEndYmd": max(p["end"] for p in periods),
        "aplyPeriods": periods,
    }


def section(value):
    # RAG 텍스트용: 값 없으면 "없음"으로 명시 (라벨 자체를 없애면 "정보가 없다"는 신호가 사라짐)
    return clean_text(value) or "없음"


structured_data = []
rag_documents = []

for p in all_policies:
    # 구조화 데이터 만들 때
    row = {k: clean_structured_field(k, p.get(k)) for k in FILTER_FIELDS}
    row["zipCdList"] = row["zipCd"].split(",") if row.get("zipCd") else []  # 지역코드 리스트화
    row.update(parse_aply_ymd(row.get("aplyYmd")))

    for field in SINGLE_CODE_FIELDS:
        row[f"{field}Nm"] = decode_code(field, row[field]) if row.get(field) else None

    for field in MULTI_CODE_FIELDS:
        codes = row[field].split(",") if row.get(field) else []
        row[f"{field}List"] = codes
        row[f"{field}NmList"] = [decode_code(field, c) for c in codes]

    structured_data.append(row)

    # 신청기간: 날짜 있으면 그 기간, 없으면 상시/마감 같은 구분명, 그것도 없으면 "없음"
    if row.get("aplyStartYmd") and row.get("aplyEndYmd"):
        aply_period_text = f"{row['aplyStartYmd']} ~ {row['aplyEndYmd']}"
    else:
        aply_period_text = row.get("aplyPrdSeCdNm") or "없음"

    # RAG 텍스트 만들 때 clean_text 적용
    text = f"""정책명: {section(p.get('plcyNm'))}
정책설명: {section(p.get('plcyExplnCn'))}
지원내용: {section(p.get('plcySprtCn'))}
신청기간: {aply_period_text}
신청방법: {section(p.get('plcyAplyMthdCn'))}
추가자격조건: {section(p.get('addAplyQlfcCndCn'))}
참여제한대상: {section(p.get('ptcpPrpTrgtCn'))}
제출서류: {section(p.get('sbmsnDcmntCn'))}"""
    rag_documents.append({"plcyNo": p.get("plcyNo"), "text": text.strip()})

# 저장
with open(os.path.join(DATA_DIR, "policies_structured.json"), "w", encoding="utf-8") as f:
    json.dump(structured_data, f, ensure_ascii=False, indent=2)

with open(os.path.join(DATA_DIR, "policies_rag_docs.json"), "w", encoding="utf-8") as f:
    json.dump(rag_documents, f, ensure_ascii=False, indent=2)

print(f"구조화 데이터 {len(structured_data)}건, RAG 문서 {len(rag_documents)}건 저장 완료")
