"""포스터·현수막 이미지 OCR."""

from __future__ import annotations

import io
import re

_reader = None


def get_ocr():
    global _reader
    if _reader is None:
        import sys

        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        try:
            import easyocr
        except ImportError as error:
            raise RuntimeError("이미지 OCR을 위해 easyocr가 필요합니다.") from error
        # Windows cp949 콘솔에서 진행률 블록문자가 깨지므로 반드시 verbose=False.
        _reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    return _reader


def read_image(data: bytes) -> tuple[str, str]:
    import numpy as np
    from PIL import Image

    lines = get_ocr().readtext(
        np.array(Image.open(io.BytesIO(data)).convert("RGB")), detail=0, paragraph=True
    )
    text = re.sub(r"[ \t]+", " ", "\n".join(lines)).strip()
    note = "" if text else "글자를 찾지 못했어요. 더 선명한 사진으로 다시 올려보세요."
    return text, note
