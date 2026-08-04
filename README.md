# 청년정책도우미 (Youth Policy Navigator)

> 경북대학교 AI·BigData 전문가 양성과정 KDT 14기 · 웹 프로젝트 **3팀**
> Module 13. 웹 기반 AI 서비스 / Module 14. 클라우드 기반 AI 서비스 미니 프로젝트

---

## 1. 프로젝트 개요

### 배경

수많은 청년 지원 정책이 존재하지만, 복잡한 자격 조건과 어려운 공고문 용어 때문에 정작 필요한 청년이 혜택을 놓치는 일이 반복된다. 정책은 흩어져 있고, 공고문은 PDF로만 배포되며, 지역별 사업은 어디서 찾아야 할지조차 알기 어렵다.

### 목표

텍스트·문서·지도 등 여러 인터페이스를 통해 청년이 정책 정보를 쉽게 탐색하고, **자신에게 맞는 혜택을 즉시 파악**할 수 있게 돕는 RAG 기반 AI 웹 서비스를 만든다.

### 목표 이용자

정책 정보 탐색에 어려움을 겪는 2030 청년층

### 핵심 차별점

일반 문서 QA 챗봇과 달리, **같은 질문이라도 사용자 조건에 따라 답이 달라진다.**

> "나에게 적용되는 청년 정책이 뭘까?"

이 한 문장에 답하려면 나이·지역·취업상태·소득구간을 알아야 한다. 조건을 입력하면 그 사용자 전용 챗봇으로 동작하고, 입력하지 않으면 전체 기준으로 답한다. 이 조건 매칭이 본 프로젝트 RAG 설계의 중심축이다.

---

## 2. 기능

### 우선순위 정의

| 등급 | 의미 |
|:---:|---|
| **P0** | 필수. 평가 항목에 직결되며 이것 없이는 프로젝트가 성립하지 않음 |
| **P1** | 핵심 차별화. 구현 비용 대비 점수 기여가 큼 |
| **P2** | 임팩트 큼. 시연에서 가장 눈에 띔 |
| **P3** | 도전 과제. 기술 리스크가 있어 별도 판단 필요 |

### F1. 정책 챗봇 + 맞춤형 자격 진단 — **P0**

- 사용자 조건 입력(나이 / 지역 / 취업상태 / 소득구간 / 학력)
- 조건에 맞는 정책만 필터링하여 검색 → 신청 가능 여부와 근거를 함께 안내
- 조건 미입력 시 전체 기준으로 응답
- 답변에 **출처 표시** (정책명 · 소관기관 · 원문 링크 · 페이지)
- 토큰 스트리밍 응답

### F2. 다중 PDF 공고문 분석 — **P1**

- 채팅 입력창 옆 `+` 버튼으로 파일 첨부 (Claude / ChatGPT 방식)
- 여러 PDF를 한 번에 업로드 → 핵심 내용 추출 및 요약
- 업로드한 문서는 해당 세션 컨텍스트로만 사용, 기본 지식베이스와 분리
- 표 형태의 자격요건 파싱 지원

### F3. 지도 기반 지역별 정책 탐색 — **P2**

- 카카오맵 위에 행정구역 폴리곤 오버레이
- 지역에 마우스를 올리면 색상 변화 (hover)
- 클릭하면 해당 지역으로 애니메이션 확대 + 오른쪽에서 정책 목록 패널이 슬라이드 인
- `X` 클릭 시 원래 축척으로 애니메이션 복귀
- 패널의 정책을 클릭하면 챗봇으로 이어짐

### F4. 포스터 / 현수막 이미지 인식 — **P3**

- 길거리 현수막, 게시판 포스터, SNS 카드뉴스 사진 업로드
- OCR로 텍스트 추출 → 해당 정책을 지식베이스에서 찾아 설명
- **리스크**: 한국어 OCR 정확도, VLM 모델의 메모리 요구량, HF Spaces 무료 티어(CPU)에서의 구동 가능성.
  Phase 3에서 기술 검증 후 진행 여부를 결정한다. 대안으로 OCR(EasyOCR) + 기존 LLM 조합을 먼저 시도한다.

---

## 3. 기술 스택

| 구분 | 기술 | 선정 이유 |
|---|---|---|
| Frontend | **Flask** + Jinja2 | Module 13 Lecture 1 정식 커리큘럼. 지도·파일첨부 등 커스텀 인터랙션 자유도 확보 |
| UI | HTML / CSS / Vanilla JS | 프레임워크 없이 DOM을 직접 제어. 애니메이션·이벤트를 원하는 대로 구현 |
| 지도 | **Kakao Maps JS SDK** | 폴리곤 오버레이, hover 이벤트, 애니메이션 확대 지원 |
| Backend | **FastAPI** + Uvicorn | 평가 항목 명시. Pydantic 기반 자동 OpenAPI 문서 |
| 검증/계약 | **Pydantic** | 팀 간 인터페이스 계약을 코드로 고정 |
| RAG | **LangChain** (LCEL) | 리트리버 조합·체인 구성 |
| Vector DB | **Chroma** | 로컬 영속화, 메타데이터 필터링 지원 |
| Embedding | `paraphrase-multilingual-MiniLM-L12-v2` | 한국어 지원, 경량 |
| 하이브리드 검색 | **BM25 + Dense** (`EnsembleRetriever`) | 정책명·기관명 등 고유명사에 강함 |
| LLM | `Qwen/Qwen2.5-0.5B-Instruct` | 수업 기준 모델. CPU 구동 가능 |
| RDB | **SQLite** | 대화 이력, 문서 메타, 사용자 프로필, 피드백 |
| 배포 | **Docker** / Docker Hub / **Hugging Face Spaces** | Module 14 평가 항목 |
| 협업 | **Git / GitHub** (Issue · Branch · PR) | Module 14 평가 항목 |

### 프론트엔드로 Flask를 선택한 이유

Module 13 평가 항목은 `Frontend / Streamlit` 으로 표기되어 있으나, 실제 평가 기준 문구는 *"기본 User Interface 설계가 제대로 동작하는가? 기존 수업에서 다루지 않은 UI 컴포넌트를 추가하고 기능 구현을 완성하였는가?"* 로 특정 프레임워크를 요구하지 않는다. Flask와 Jinja2는 Module 13 Lecture 1에서 라우팅·템플릿·매크로·정적파일·세션까지 정식으로 다룬 범위다.

기술적 이유는 두 가지다.

1. **지도 인터랙션** — hover 색상 전환, 클릭 시 애니메이션 확대, 슬라이드 패널은 DOM과 CSS를 직접 제어해야 자연스럽게 나온다. Streamlit은 상호작용마다 스크립트를 처음부터 다시 실행하므로 연속 애니메이션에 불리하다.
2. **파일 첨부 UX** — 입력창 옆 `+` 버튼으로 첨부하는 방식은 커스텀 DOM 제어가 필요하다.

> 평가 항목 표기가 Streamlit인 만큼, 착수 전 담당 교수에게 프레임워크 변경 가능 여부를 확인한다.

---

## 4. 시스템 아키텍처

```
                     브라우저
┌──────────────────────────────────────────────┐
│  HTML · CSS · JS                             │
│  ├ 💬 챗봇  ├ 🗺 지도  ├ 📚 문서              │
│  └ 사이드바: 내 조건 입력                      │
└───────┬──────────────────────┬───────────────┘
        │ 페이지 요청           │ fetch · SSE (CORS)
        ▼                      │
┌───────────────────┐          │
│ Flask  :5000      │          │
│ 라우팅 · 템플릿    │          │
│      [이수민]      │          │
└───────────────────┘          │
                               ▼
┌──────────────────────────────────────────────┐
│  FastAPI Backend  :8000           [최성호]    │
│  routers/  schemas.py  db.py                 │
└───────┬──────────────────────┬───────────────┘
        ▼                      ▼
┌───────────────────┐  ┌───────────────────────┐
│  rag/    [박준혁]  │  │  ingest/    [김영민]   │
│  검색·프롬프트·생성 │  │  수집·정규화·인덱싱     │
└─────────┬─────────┘  └──────────┬────────────┘
          │      읽기        쓰기  │
          └────────┬───────────────┘
                   ▼
        ┌────────────────────┐
        │ Chroma  │  SQLite  │
        └────────────────────┘
```

### Flask는 화면만, 데이터는 브라우저가 직접

Flask는 **페이지 렌더링만** 담당하고, 정책 검색·챗봇 응답 등 데이터는 **브라우저 JS가 FastAPI를 직접 호출**한다.

Flask가 FastAPI를 서버 사이드로 프록시하면 FastAPI가 사실상 내부 함수 호출처럼 되어, Swagger 문서와 실제 사용 경로가 어긋난다. 브라우저가 직접 호출하면 `/docs`에 정의된 API가 곧 실제로 쓰이는 API가 되어 REST 설계가 그대로 드러난다.

- Flask `:5000` → 페이지(HTML) 응답
- FastAPI `:8000` → 데이터(JSON · SSE) 응답
- 포트가 다르므로 **교차 출처**가 되어 백엔드에 `CORSMiddleware` 필요

### 데이터 파이프라인 두 갈래

| | 기본 지식베이스 | 세션 업로드 |
|---|---|---|
| 입력 | 정책 JSON 데이터 | 사용자가 올린 PDF / 이미지 |
| 시점 | 사전 구축 (배포 전) | 런타임 |
| 저장 | Chroma `policies` 컬렉션 (영속) | Chroma 임시 컬렉션 (세션 종료 시 정리) |
| 담당 | 김영민 | 김영민 (파싱) + 박준혁 (검색 병합) |

기본 지식베이스와 사용자 업로드 문서를 **분리**하는 것이 핵심이다. 섞으면 다른 사용자의 업로드가 내 답변에 새어 들어간다.

---

## 5. 프로젝트 구조

디렉터리 하나가 담당자 한 명에 대응한다. 소유자가 아닌 사람은 해당 디렉터리를 직접 수정하지 않고 Issue 또는 PR 리뷰로 요청한다.

```
team-13-project/
├── src/
│   ├── frontend/                    ← 이수민
│   │   ├── app.py                   # Flask 앱 · Blueprint 등록
│   │   ├── views/
│   │   │   ├── chat.py              # F1 챗봇 페이지
│   │   │   ├── map.py               # F3 지도 페이지
│   │   │   └── documents.py         # F2 문서 페이지
│   │   ├── templates/
│   │   │   ├── base.html            # 공통 레이아웃 (상속용)
│   │   │   ├── chat.html
│   │   │   ├── map.html
│   │   │   ├── documents.html
│   │   │   └── macros/
│   │   │       ├── message.html     # 말풍선 매크로
│   │   │       └── source_card.html # 출처 카드 매크로
│   │   ├── static/
│   │   │   ├── css/  base.css · chat.css · map.css
│   │   │   ├── js/   chat.js · map.js · profile.js · upload.js
│   │   │   └── img/
│   │   ├── api_client.py            # 백엔드 호출 래퍼 (MOCK 모드 포함)
│   │   └── config.py
│   │
│   ├── backend/                     ← 최성호
│   │   ├── api.py                   # FastAPI 앱, CORS, lifespan
│   │   ├── routers/
│   │   │   ├── chat.py              # /ask, /ask/stream
│   │   │   ├── documents.py         # /documents
│   │   │   ├── policies.py          # /policies (지도용)
│   │   │   └── vision.py            # /vision (P3)
│   │   ├── schemas.py               # ★ Pydantic 계약 (전원 참조)
│   │   ├── db.py                    # SQLite
│   │   └── deps.py                  # Depends 주입
│   │
│   ├── rag/                         ← 박준혁
│   │   ├── retriever.py             # 하이브리드 검색 + 메타 필터
│   │   ├── generator.py             # 프롬프트 + 생성 + 스트리밍
│   │   ├── eligibility.py           # 자격 진단 로직
│   │   └── prompts.py               # 프롬프트 템플릿
│   │
│   └── ingest/                      ← 김영민
│       ├── collect.py               # 정책 JSON 수집
│       ├── normalize.py             # 스키마 정규화 + 메타데이터 추출
│       ├── indexer.py               # 청킹 → 임베딩 → Chroma 적재
│       ├── pdf.py                   # PDF 파싱 (표 포함)
│       └── vision.py                # 이미지 OCR (P3)
│
├── data/
│   ├── policies.json                # 원본 정책 데이터
│   └── regions.geojson              # 행정구역 폴리곤
├── chroma_db/                       # 벡터 DB (gitignore)
├── app.db                           # SQLite (gitignore)
├── tests/
├── docs/
│   └── presentation/                # 발표 자료
├── requirements.txt
├── Dockerfile.ui
├── Dockerfile.api
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 6. 역할 분담

**팀 구성: 4인 1팀**

| 이름 | 역할 | Module 13 | Module 14 | 소유 디렉터리 |
|---|---|---|---|---|
| **최성호** | 팀장 · Backend Engineer | 총괄·일정 관리 / FastAPI 서비스 · API 계약 설계 | Git 브랜치 전략 · PR 리뷰 운영 / `Dockerfile.api` | `src/backend/` |
| **박준혁** | AI Engineer (LLM · RAG) | 하이브리드 검색 / 프롬프트 설계 / 자격 진단 / 생성·스트리밍 | AI 모듈 통합 · `docker-compose.yml` | `src/rag/` |
| **김영민** | AI Engineer (Data · Ingest) | 정책 데이터 수집·정규화 / PDF 파싱 / 인덱싱 파이프라인 | Hugging Face Spaces 배포 · CI/CD | `src/ingest/` |
| **이수민** | Frontend Engineer | Flask 라우팅·템플릿 / 카카오맵 / 챗봇 UI / 조건 입력 UX | `Dockerfile.ui` · Docker Hub push | `src/frontend/` |

### 공동 책임

- **`src/backend/schemas.py`** — 최성호가 소유하되 변경은 반드시 PR + 전원 리뷰. 이 파일이 네 사람의 작업을 연결한다.
- **`requirements.txt`** — 각자 추가 시 PR로만. 버전을 고정(`==`)한다.
- **발표 자료** — 발표는 1인당 5분이므로 각자 자기 파트 슬라이드를 작성하고 최성호가 취합·통합한다.

### 업무량 분산 원칙

교수 자료의 기본안은 팀장에게 개발 롤을 두지 않는다(M13 총괄, M14 DevOps). 본 팀은 팀장이 Backend를 겸하므로, Module 14의 배포 작업(Git 20점 · Docker 20점 · Spaces 20점)을 한 사람에게 몰지 않고 아래와 같이 나눈다.

- Git 브랜치 전략 · PR · Issue 운영 → **최성호**
- Docker Compose 및 멀티 컨테이너 통합 → **박준혁**
- Hugging Face Spaces 배포 및 CI/CD → **김영민**
- 각자의 Dockerfile은 각자 작성 → **전원**

---

## 7. API 명세

전체 명세는 서버 기동 후 `http://localhost:8000/docs` 에서 확인한다.

### 챗봇

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/ask` | `AskRequest` | `AskResponse` |
| `GET` | `/ask/stream` | `AskRequest` (query) | SSE 토큰 스트림 |
| `POST` | `/eligibility` | `UserProfile` | `EligibilityResponse` |

### 문서

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/documents` | `list[UploadFile]` | `list[DocumentResponse]` |
| `GET` | `/documents` | – | `list[DocumentResponse]` |
| `DELETE` | `/documents/{doc_id}` | – | `DeleteResponse` |

### 정책 · 지도

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/policies` | `region`, `category`, `page`, `size` | `PolicyListResponse` |
| `GET` | `/policies/{policy_id}` | – | `PolicyDetail` |
| `GET` | `/regions/summary` | – | `list[RegionSummary]` (지역별 정책 수) |

### 세션 · 피드백

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/sessions/{sid}/messages` | – | `list[Message]` |
| `POST` | `/feedback` | `FeedbackRequest` | `OkResponse` |

### 주요 스키마

```python
class UserProfile(BaseModel):
    age: int | None = None
    region: str | None = None          # 시도 · 시군구
    employment: EmploymentStatus | None = None
    income_bracket: int | None = None  # 중위소득 %
    education: str | None = None

class AskRequest(BaseModel):
    question: str
    session_id: str
    profile: UserProfile | None = None
    top_k: int = 5
    mode: SearchMode = SearchMode.HYBRID   # vector | bm25 | hybrid
    doc_ids: list[str] = []                # 세션 업로드 문서 한정 검색

class Source(BaseModel):
    doc_id: str
    title: str          # 정책명
    organization: str   # 소관기관
    page: int | None
    snippet: str
    score: float
    url: str | None

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    matched_policies: list[str]
    session_id: str
    elapsed_ms: int
```

> `profile`이 `None`이거나 모든 필드가 비어 있으면 조건 필터 없이 전체 기준으로 검색한다.

---

## 8. 개발 순서

### Phase 0 — 합의와 골격 (전원 · 동시)

가장 중요한 단계다. **이 단계가 끝나야 네 사람이 병렬로 갈라질 수 있다.**

| # | 작업 | 담당 |
|---|---|---|
| 0-1 | 기능 우선순위 · 일정 확정, GitHub Issue 등록 | 최성호 |
| 0-2 | **`schemas.py` 확정 후 `main`에 선(先)머지** | 최성호 (전원 리뷰) |
| 0-3 | 디렉터리 골격 · `requirements.txt` · `.env.example` | 최성호 |
| 0-4 | 정책 데이터 출처 확정, 샘플 30건 확보 | 김영민 |
| 0-5 | 브랜치 보호 규칙 · PR 템플릿 · Issue 템플릿 | 최성호 |
| 0-6 | `api_client.py` **MOCK 모드** · `base.html` 레이아웃 | 이수민 |

`0-6`은 프론트가 백엔드 완성을 기다리지 않게 하는 장치다. `USE_MOCK=true`면 `schemas.py` 형태의 가짜 응답을 반환하므로, 이수민은 UI를 끝까지 혼자 만들 수 있다.

### Phase 1 — 핵심 챗봇 (P0)

| 담당 | 작업 |
|---|---|
| 김영민 | 정책 JSON 정규화 → 메타데이터(나이·지역·소득·기간) 추출 → 청킹 → Chroma 적재 |
| 박준혁 | 벡터 검색 + 프로필 메타 필터 → 프롬프트 → 생성 |
| 최성호 | `POST /ask` · SQLite 대화 저장 · CORS · lifespan 모델 로딩 |
| 이수민 | 챗봇 페이지 · 말풍선 렌더 · 조건 입력 폼 · 출처 카드 |

**Phase 1 종료 조건**: 조건을 넣고 뺐을 때 답이 달라지는 것이 눈으로 확인된다.

### Phase 2 — 문서 · 지도 (P1 · P2)

| 담당 | 작업 |
|---|---|
| 김영민 | 다중 PDF 파싱 · 표 추출 · 세션 임시 컬렉션 |
| 박준혁 | **하이브리드 검색**(BM25+Dense) · 프롬프트 개선 · 검색 성능 비교 실험 |
| 최성호 | `/documents` · `/policies` · `/regions/summary` · SSE 스트리밍 |
| 이수민 | `+` 첨부 UI · **카카오맵 인터랙션** · SSE 수신 · 검색모드 비교 UI |

### Phase 3 — 이미지 인식 (P3 · 조건부)

먼저 **기술 검증**부터 한다. 샘플 포스터 5장으로 OCR 정확도와 메모리 사용량을 측정하고, 팀 회의에서 진행 여부를 결정한다. 중단하기로 해도 검증 과정 자체를 발표에 포함한다.

| 담당 | 작업 |
|---|---|
| 김영민 | OCR 파이프라인 · 이미지 전처리 |
| 박준혁 | 추출 텍스트 → 정책 매칭 |
| 최성호 | `POST /vision` |
| 이수민 | 이미지 업로드 · 인식 결과 UI |

### Phase 4 — 배포 (Module 14)

| 담당 | 작업 |
|---|---|
| 이수민 | `Dockerfile.ui` (Flask + gunicorn) · Docker Hub push |
| 최성호 | `Dockerfile.api` (8000) · Docker Hub push · Git 히스토리 정리 |
| 박준혁 | `docker-compose.yml` · 서비스 간 네트워크 · 통합 테스트 |
| 김영민 | HF Spaces (`sdk: docker`, `app_port: 7860`) · CI/CD · 배포 문제 해결 기록 |

**포트 주의**: Hugging Face Docker Space는 기본 포트가 `7860`이다. Space `README.md`의 `app_port`, `Dockerfile`의 `EXPOSE`, gunicorn `--bind` 값을 모두 맞춰야 한다.

**개발 서버 금지**: `flask run`의 내장 서버는 개발 전용이다. 컨테이너에서는 `gunicorn`으로 서빙한다. 이 역시 수업에서 다루지 않은 항목이다.

**Chroma DB 주의**: 벡터 DB를 이미지에 포함할지, Space 기동 시 생성할지 Phase 2 종료 전까지 결정한다. 포함하면 이미지가 커지고, 생성하면 콜드 스타트가 느려진다.

---

## 9. Git 협업 규칙

Module 14 평가에 *"브랜치, 커밋, PR, Issue 등을 적절히 활용했는가"* 가 명시되어 있다. **`main`에 직접 push 하지 않는다.**

### 브랜치

```
main                    보호 브랜치. PR 병합으로만 갱신
 ├── feature/ui-chat
 ├── feature/ui-map
 ├── feature/api-ask
 ├── feature/rag-hybrid
 ├── feature/ingest-policies
 ├── fix/map-popup-zindex
 └── docs/readme
```

`feature/<영역>-<작업>` 형식을 쓴다. 영역은 `ui` · `api` · `rag` · `ingest` 중 하나.

### 커밋 메시지

```
<type>(<scope>): <제목>

<본문 — 왜 이렇게 했는지>

Closes #12
```

| type | 용도 |
|---|---|
| `feat` | 기능 추가 |
| `fix` | 버그 수정 |
| `docs` | 문서 |
| `refactor` | 동작 변화 없는 구조 개선 |
| `test` | 테스트 |
| `chore` | 빌드·설정·의존성 |

scope는 `ui` · `api` · `rag` · `ingest` · `docker` 중 하나.

```
feat(ui): 카카오맵 지역 클릭 시 확대 애니메이션 추가
fix(rag): 프로필 미입력 시 메타 필터가 전체를 제외하던 문제 수정
chore(docker): UI 컨테이너 포트를 7860으로 변경
```

### 작업 흐름

```
1. Issue 생성            작업 단위 = Issue 하나
2. 브랜치 생성           git switch -c feature/ui-map
3. 커밋                  의미 단위로 쪼개서. "작업 끝" 같은 뭉텅이 커밋 금지
4. push                  git push -u origin feature/ui-map
5. PR 생성               제목 = Issue 제목, 본문에 Closes #N
6. 리뷰                  최소 1명 승인. 팀장은 전 PR 확인
7. Squash merge          main 히스토리를 읽을 수 있게 유지
8. 브랜치 삭제           로컬·원격 모두
```

### 충돌 예방

- 남의 디렉터리를 직접 고치지 않는다. 필요하면 Issue를 열어 소유자에게 요청한다.
- `schemas.py` 변경은 반드시 팀 채널에 공지 후 PR. 계약이 바뀌면 네 명 모두 영향받는다.
- 작업 시작 전 `git switch main && git pull` 을 습관화한다.
- 하루가 끝나면 미완성이어도 push 한다. 로컬에만 쌓아두지 않는다.

---

## 10. 실행 방법

### 로컬

```bash
git clone https://github.com/knukdt14/team-13-project.git
cd team-13-project

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # KAKAO_MAP_KEY, HF_TOKEN 등 입력

python -m src.ingest.indexer     # 최초 1회, 벡터 DB 구축

uvicorn src.backend.api:app --reload --port 8000              # 터미널 1
flask --app src/frontend/app.py run --debug --port 5000       # 터미널 2
```

| 주소 | 설명 |
|---|---|
| http://localhost:5000 | 서비스 화면 (Flask) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |

### Docker

```bash
docker compose up --build
```

### 환경 변수

| 이름 | 설명 |
|---|---|
| `KAKAO_MAP_KEY` | 카카오맵 JavaScript 키. 사용 도메인 등록 필요 |
| `HF_TOKEN` | Hugging Face 토큰 |
| `API_URL` | 브라우저 JS가 호출할 백엔드 주소 (기본 `http://localhost:8000`) |
| `USE_MOCK` | `true`면 프론트가 가짜 응답 사용 (백엔드 없이 UI 개발) |
| `FLASK_SECRET_KEY` | Flask 세션 서명 키 |
| `CHROMA_DIR` | 벡터 DB 경로 (기본 `./chroma_db`) |

> **카카오맵 키 주의**: JavaScript 키는 카카오 개발자 콘솔에 **사용 도메인을 등록**해야 동작한다. 로컬(`http://localhost:5000`)과 배포 도메인(`https://<space>.hf.space`)을 모두 등록한다. Phase 2 시작 전에 미리 발급받아 둘 것.

---

## 11. 평가 기준 대응

### Module 13 (100점)

| 항목 | 배점 | 대응 |
|---|:---:|---|
| Frontend | 20 | Blueprint 라우팅, 템플릿 상속(`base.html`), Jinja2 매크로, **카카오맵 인터랙션**, `+` 파일 첨부, SSE 스트리밍 수신 |
| Backend / FastAPI | 20 | **Pydantic `response_model`**, `APIRouter`, `Depends`, `HTTPException`, `lifespan`, `CORSMiddleware`, SSE 스트리밍 |
| LLM / RAG | 20 | **하이브리드 검색**(BM25+Dense), 프로필 기반 메타데이터 필터, 프롬프트 설계, 검색 모드별 성능 비교 |
| 발표 및 시연 | 20 | 디렉터리 = 담당자 구조, Issue·PR 히스토리로 협업 과정 증빙 |
| 프로젝트 완성도 | 20 | `frontend` / `backend` / `rag` / `ingest` 4계층 분리 |

### Module 14 (100점)

| 항목 | 배점 | 대응 |
|---|:---:|---|
| Git / GitHub | 20 | 보호된 `main`, `feature/*` 브랜치, Conventional Commits, PR 리뷰, Issue 연동 |
| Docker / Docker Hub | 20 | UI·API 이미지 분리, 레이어 캐시를 고려한 Dockerfile, Docker Hub 태그 관리 |
| Hugging Face Spaces | 20 | Docker SDK Space 배포, 포트 7860 전환, CI/CD |
| 발표 및 시연 | 20 | 배포 중 발생한 문제와 해결 과정 기록 |
| 프로젝트 완성도 | 20 | Compose 기반 멀티 컨테이너 통합 동작 |

### "수업에서 다루지 않은 것" 대조표

두 모듈 모두 만점 조건이 *기존 수업에서 다루지 않은 요소의 추가*다.

| 영역 | 수업 범위 (기본점) | 본 프로젝트 추가분 |
|---|---|---|
| Frontend | `@app.route` · URL 변수 · `request.args/form` · `render_template` · Jinja2 매크로 · `send_from_directory` · `session` | **Blueprint** · 템플릿 상속(`{% extends %}`) · `url_for` 정적파일 관리 · **fetch 비동기 통신** · **SSE 스트리밍 수신** · localStorage · CSS 트랜지션 · **카카오맵 SDK 연동** |
| Backend | `Form(...)` · 생 `dict` 반환 · `UploadFile` · `StreamingResponse` | **Pydantic 모델 · `response_model`** · `APIRouter` · `Depends` · `lifespan` · CORS · SSE |
| RAG | `PyPDFLoader` · `RecursiveCharacterTextSplitter` · `similarity_search(k=3)` | **하이브리드 검색** · 메타데이터 필터 · 표 파싱 · 다중 문서 · 검색 성능 비교 |
| Data | 단일 PDF 로드 | **JSON 정책 데이터 정규화** · SQLite 이력 관리 · 세션별 컬렉션 분리 |

> 수업의 Flask 예제는 form을 POST하고 페이지 전체를 다시 그리는 방식이다. 본 프로젝트는 **fetch 기반 비동기 통신**과 **SSE 토큰 스트리밍**으로 페이지 전환 없이 동작하며, 이것이 프론트엔드의 핵심 차별 요소다.

---

## 12. 팀

| 이름 | 역할 | GitHub |
|---|---|---|
| 최성호 | 팀장 · Backend Engineer | |
| 박준혁 | AI Engineer (LLM · RAG) | |
| 김영민 | AI Engineer (Data · Ingest) | |
| 이수민 | Frontend Engineer | |

경북대학교 AI·BigData 전문가 양성과정 KDT 14기 · Module 13 & 14 미니 프로젝트
지도: 배준현 교수 (경북대학교)
