"""AI 서비스 패키지.

``src/rag`` 의 검색기(PolicyRetriever)와 생성기(SolarGenerator)를 HTTP로
노출하는 얇은 서버 계층이다. 무거운 모델과 FAISS 인덱스는 이 컨테이너에만
올라가고, 백엔드는 HTTP로 결과만 받아 간다.

ASGI 앱은 ``src.ai.main:app`` 에서 가져온다.
"""
