"""정책 수집·정규화·인덱싱 파이프라인.

여기서 하위 모듈을 import 하지 않는다.

`collect.py` 처럼 최상위에 실행 코드가 있는 스크립트가 섞여 있어서, 패키지를
import 하는 것만으로 온통청년 API 수집이 시작된다. 실제로
`python -m src.ingest.collect` 를 돌렸을 때 수집이 두 번 시작됐다.

각 모듈은 직접 실행하거나 명시적으로 import 한다.

    python src/ingest/collect.py
    python src/ingest/normalize.py
"""
