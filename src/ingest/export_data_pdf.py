# scripts/export_data_pdf.py
# policies_structured.json / policies_rag_docs.json 내용을 사람이 읽기 좋은 PDF로 변환
import sys
import os
import json
import re
from fpdf import FPDF

sys.stdout.reconfigure(encoding="utf-8")

FONT = r"C:\Windows\Fonts\malgun.ttf"
FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def wrap_long_tokens(text, chunk=40):
    # 콤마 뒤에 줄바꿈 가능한 공백 추가 (우편번호 나열 등이 숫자 중간에 안 잘리도록)
    text = re.sub(r",(?!\s)", ", ", text)
    # 그래도 남는, 공백 없이 아주 긴 단어(URL 등)는 fpdf가 줄바꿈을 못 해서 에러남 -> 마지막 수단으로 강제 삽입
    return re.sub(rf"(\S{{{chunk}}})", r"\1 ", text)


def mc(pdf, h, text, fill=False):
    # multi_cell 기본값이 커서를 오른쪽 끝에 남겨서, 다음 줄 쓸 공간이 없어지는 문제 방지
    pdf.multi_cell(0, h, text, fill=fill, new_x="LMARGIN", new_y="NEXT")


def new_pdf():
    pdf = FPDF()
    pdf.add_font("Malgun", "", FONT)
    pdf.add_font("Malgun", "B", FONT_BOLD)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    return pdf


# ---------- policies_structured.json ----------
with open(os.path.join(DATA_DIR, "policies_structured.json"), encoding="utf-8") as f:
    structured = json.load(f)

pdf = new_pdf()
for i, row in enumerate(structured, 1):
    pdf.set_font("Malgun", "B", 10.5)
    pdf.set_fill_color(235, 240, 250)
    title = f"{i}. {row.get('plcyNm') or ''}"
    mc(pdf, 6, title, fill=True)
    pdf.set_font("Malgun", "", 9)
    for k, v in row.items():
        if k == "plcyNm" or v in (None, "", []):
            continue
        mc(pdf, 5, wrap_long_tokens(f"  {k}: {v}"))
    pdf.ln(2)

pdf.output(os.path.join(DATA_DIR, "policies_structured.pdf"))
print(f"policies_structured.pdf 저장 완료 ({len(structured)}건)")

# ---------- policies_rag_docs.json ----------
with open(os.path.join(DATA_DIR, "policies_rag_docs.json"), encoding="utf-8") as f:
    rag_docs = json.load(f)

pdf = new_pdf()
for i, doc in enumerate(rag_docs, 1):
    pdf.set_font("Malgun", "B", 10)
    pdf.set_fill_color(235, 250, 235)
    mc(pdf, 6, f"{i}. plcyNo: {doc.get('plcyNo')}", fill=True)
    pdf.set_font("Malgun", "", 9)
    mc(pdf, 5, wrap_long_tokens(doc.get("text", "")))
    pdf.ln(3)

pdf.output(os.path.join(DATA_DIR, "policies_rag_docs.pdf"))
print(f"policies_rag_docs.pdf 저장 완료 ({len(rag_docs)}건)")
