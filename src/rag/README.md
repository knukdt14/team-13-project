# BGE-M3 + Solar 청년정책 검색·터미널 챗봇

다른 팀원의 파일을 수정하지 않고 `src/rag` 폴더 안에서만 동작한다. PDF는
사용하지 않으며 다음 JSON만 읽는다.

- `../data/policies_rag_docs.json`: 검색 문서 2,693건
- `../data/policies_structured.json`: 조건 필터와 응답 메타데이터

연령 제한 플래그는 온통청년 데이터 기준으로 `N=제한 있음`, `Y=제한 없음`으로
판정한다. 나이 범위가 0 또는 결측이면 오탐 방지를 위해 후보에서 제외하지 않는다.

## 폴더 구조

```text
src/
└── rag/
    ├── retriever.py      # BGE-M3 + BM25 하이브리드 Top-K 검색
    ├── generator.py      # Solar 답변 생성과 스트리밍
    ├── eligibility.py    # 질문 조건 추출과 정책 자격 판정 공개 모듈
    ├── prompts.py        # Solar 시스템 프롬프트
    ├── core/             # 설정, 데이터 로더, GPU, 검색 보조 구현
    ├── cli/              # 인덱스 생성, 검색 점검, 터미널 챗봇
    ├── storage/          # FAISS 인덱스와 청크 메타데이터
    └── tests/            # 조건 추출, 필터링, 하이브리드 검색 테스트
```

## 구현 범위

```text
사용자 질문
  -> 조건 추출(age, region, employment, education, income_bracket)
  -> 나이·지역·직업·학력·소득·접수기간 정확 필터
  -> BGE-M3 GPU Dense 검색 + BM25 검색
  -> Reciprocal Rank Fusion 하이브리드 순위
  -> policy_id 중복 제거 및 Top-K
  -> Solar API 스트리밍 답변 + 정책 출처
```

| 항목 | 사용 기술 |
|---|---|
| 임베딩 | `BAAI/bge-m3` (1024차원, 최대 1024토큰) |
| 임베딩 장치 | RTX 4070 Laptop GPU, CUDA, FP16 |
| Dense 인덱스 | FAISS cosine (`IndexFlatIP`) |
| 키워드 검색 | BM25 + 한국어 2-gram |
| 기본 검색 | Dense 0.6 + BM25 0.4 RRF 하이브리드 |
| 생성 LLM | Upstage `solar-pro3` API |

> README의 Chroma를 실험했으나 이 노트북의 Windows + Chroma 1.5.9에서 큰
> Persistent HNSW 컬렉션이 재시작 후 열리지 않는 문제가 재현됐다. 실행 가능한
> 결과를 우선해 FAISS 영속 인덱스를 기본값으로 사용한다. Chroma는
> `build_index --with-chroma` 실험 옵션으로만 남겨 두었다.

## GPU 환경

공유 수업 환경은 수정하지 않았다. GPU 패키지는 Git에서 제외되는
`src/rag/.venv-gpu`가 사용한다.

```cmd
src\rag\.venv-gpu\Scripts\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

현재 확인값:

```text
2.13.0+cu130 True NVIDIA GeForce RTX 4070 Laptop GPU
```

환경을 새로 만드는 경우 CUDA PyTorch가 설치된 `TF_ENV`를 먼저 활성화한 뒤:

```cmd
python -m venv --system-site-packages src\rag\.venv-gpu
src\rag\.venv-gpu\Scripts\python.exe -m pip install -r requirements.txt
src\rag\.venv-gpu\Scripts\python.exe -m pip install "transformers>=5.0,<6.0"
```

## API 키

실제 키는 Git에서 제외된 `src/rag/.env`에 저장되어 있다.

```dotenv
UPSTAGE_API_KEY=발급받은_키
UPSTAGE_MODEL=solar-pro3
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cuda
```

`.env`는 커밋하지 않는다. 팀원은 `.env.example`을 복사해 자신의 키를 넣는다.

## 터미널 챗봇 실행

프로젝트 루트에서 다음 한 줄을 실행한다.

```cmd
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.terminal_chatbot
```

또는 실행 도우미를 사용한다.

```cmd
src\rag\cli\run_chatbot.cmd
```

현재 위치가 `src\rag\cli` 폴더라면 파일을 직접 실행해도 된다. 다른 Python
환경에서 실행한 경우에도 `.venv-gpu`가 있으면 GPU 환경으로 자동 전환된다.

```cmd
python terminal_chatbot.py
```

대화 중 명령어:

- `/도움말`: 명령어 표시
- `/초기화`: 대화 기록 삭제
- `/마감포함`: 마감 정책도 검색
- `/마감제외`: 접수 중 정책만 검색
- `/종료`: 챗봇 종료

질문 한 건만 테스트하고 종료할 수도 있다.

```cmd
src\rag\cli\run_chatbot.cmd --include-closed --question "부산에 사는 28살 미취업자인데 주거 정책 알려줘"
```

## 인덱스 생성

BGE-M3 인덱스는 이미 `src/rag/storage`에 생성되어 있다. 정책 데이터나
임베딩 모델이 바뀐 경우에만 다시 실행한다.

```cmd
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.build_index --device cuda --batch-size 4 --max-seq-length 1024
```

현재 인덱스:

- 문서 수: 2,693
- 차원: 1,024
- 생성 장치: RTX 4070 GPU
- 모델 dtype: FP16
- 유사도: cosine
- 지역 메타데이터: `region_codes`(시도 코드), `is_nationwide`(전국 여부)

지역 메타데이터는 `policies_structured.json`의 `zipCdList`를 `policy_id`로 연결해
생성한다. 중복을 제거한 세부 지역코드가 200개 이상인 정책은
`is_nationwide=true`로 기록된다.

## 검색 모드 비교

```cmd
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.search_cli "부산 청년 주거 지원" --mode vector --top-k 5
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.search_cli "부산 청년 주거 지원" --mode bm25 --top-k 5
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.search_cli "부산 청년 주거 지원" --mode hybrid --top-k 5
```

기본적으로 마감 정책은 제외된다. 마감까지 보려면 `--include-closed`를 붙인다.

## 백엔드 호출 계약

```python
from src.rag import PolicyRetriever

retriever = PolicyRetriever()  # 서버 lifespan에서 한 번만 생성

result = retriever.search(
    question="제가 받을 수 있는 주거 지원을 알려줘",
    filters={
        "age": 28,
        "region": "부산",
        "employment": "미취업자",
        "education": "대학 재학",
        "income_bracket": 120,
    },
    top_k=5,
    mode="hybrid",
    include_closed=False,
)
```

이전 필드명 `job_status`, `school_status`도 각각 `employment`, `education`으로
자동 변환된다. 반환값에는 다음 정보가 들어 있다.

- `extracted_conditions`, `search_mode`, `result_count`
- `policy_id`, `policy_name`, `score`
- `dense_score`, `bm25_score`, `matched_text`
- 운영 기관, 신청 기간, 신청 URL, 소득 조건 등의 `metadata`

## 전처리 청크 연결

현재 JSON은 정책당 문서 하나다. 전처리 담당자가 다음 JSON/JSONL 청크를 주면
그 파일을 지정해 인덱스를 다시 만든다.

```json
{
  "chunk_id": "P001_eligibility_0",
  "policy_id": "P001",
  "section": "eligibility",
  "text": "신청 대상: 만 19세부터 34세까지의 부산 거주 미취업 청년"
}
```

```cmd
src\rag\.venv-gpu\Scripts\python.exe -m src.rag.cli.build_index --documents data\policy_chunks.jsonl --device cuda
```

같은 정책의 여러 청크가 검색돼도 `policy_id` 기준으로 한 정책만 반환한다.

## 테스트

```cmd
src\rag\.venv-gpu\Scripts\python.exe -m unittest discover -s src\rag\tests -v
```
