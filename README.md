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

수집한 정책 데이터가 나이·지역·소득·취업상태·학력을 코드 필드로 갖고 있어, 이 방식이 실제로 가능하다. 자세한 내용은 §5를 참고한다.

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
- 답변에 **출처 표시** (정책명 · 소관기관 · 신청 링크)
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
| Frontend | **React** + Vite | 채팅·지도의 상태 변화를 선언적으로 관리. 컴포넌트 단위 분리 |
| 라우팅 | React Router | 챗봇 / 지도 / 문서 페이지 전환 |
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

### 프론트엔드로 React를 선택한 이유

Module 13 평가 항목은 `Frontend / Streamlit` 으로 표기되어 있으나, 실제 평가 기준 문구는 *"기본 User Interface 설계가 제대로 동작하는가? 기존 수업에서 다루지 않은 UI 컴포넌트를 추가하고 기능 구현을 완성하였는가?"* 로 특정 프레임워크를 요구하지 않는다.

세 가지 이유로 React를 택했다.

1. **스트리밍 채팅** — 토큰이 도착할 때마다 메시지 목록이 갱신된다. 상태를 바꾸면 화면이 따라오는 React 모델이 DOM을 직접 조작하는 방식보다 명확하고, 메시지가 쌓여도 코드가 복잡해지지 않는다.
2. **지도 인터랙션** — hover 색상 전환, 클릭 시 애니메이션 확대, 슬라이드 패널은 지도 상태와 패널 상태를 함께 관리해야 한다. 커스텀 훅으로 묶으면 지도 로직과 화면이 분리된다.
3. **배포 구조** — Hugging Face Docker Space는 **컨테이너를 하나만** 실행한다. React를 정적 파일로 빌드해 FastAPI가 서빙하면 프로세스가 하나로 끝난다. 서버 사이드 템플릿 방식이라면 웹 서버와 API 서버 두 프로세스를 한 컨테이너에 묶어야 한다.

> 평가 항목 표기가 Streamlit인 만큼, 착수 전 담당 교수에게 프레임워크 변경 가능 여부를 확인한다.

---

## 4. 시스템 아키텍처

```
                     브라우저
┌──────────────────────────────────────────────┐
│  React SPA                        [이수민]    │
│  ├ 💬 챗봇  ├ 🗺 지도  ├ 📚 문서              │
│  └ 사이드바: 내 조건 입력                      │
└──────────────────┬───────────────────────────┘
                   │ fetch · SSE  →  /api/*
                   ▼
┌──────────────────────────────────────────────┐
│  FastAPI  :8000                   [최성호]    │
│  /api/*  →  routers/  schemas.py  db.py      │
│  /       →  StaticFiles (빌드된 SPA, 배포 시) │
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

### 개발 환경과 배포 환경이 다르다

| | 개발 | 배포 |
|---|---|---|
| 프론트 | Vite 개발 서버 `:5173` | `npm run build` → 정적 파일 |
| 서빙 | Vite가 `/api` 요청을 `:8000`으로 프록시 | FastAPI가 `StaticFiles`로 SPA 서빙 |
| CORS | **불필요** (프록시가 같은 출처로 만듦) | **불필요** (같은 서버) |
| 프로세스 | 2개 (Vite + Uvicorn) | 1개 (Uvicorn) |

Vite 프록시 덕분에 개발 중에도 CORS 설정이 필요 없다. `vite.config.js`에 다음을 넣는다.

```js
server: {
  proxy: { '/api': 'http://localhost:8000' }
}
```

### API 경로는 반드시 `/api` 로 시작한다

배포 시 FastAPI가 `/` 에서 SPA를 서빙하므로, API 라우트가 접두사 없이 `/ask` 같은 형태면 SPA 라우팅과 충돌한다. 모든 엔드포인트는 `/api` 아래에 둔다.

```python
app.include_router(chat_router, prefix="/api")
# ... 모든 라우터 등록 후, 맨 마지막에
app.mount("/", StaticFiles(directory="dist", html=True), name="spa")
```

마운트 순서가 중요하다. `StaticFiles` 마운트는 **모든 API 라우터 등록 이후**에 와야 한다.

### 데이터 흐름 두 갈래

| | 기본 지식베이스 | 세션 업로드 |
|---|---|---|
| 입력 | `data/policies_rag_docs.json` (2,693건) | 사용자가 올린 PDF / 이미지 |
| 시점 | 사전 구축 (배포 전) | 런타임 |
| 저장 | Chroma `policies` 컬렉션 (영속) | Chroma 임시 컬렉션 (세션 종료 시 정리) |
| 담당 | 김영민 | 김영민 (파싱) + 박준혁 (검색 병합) |

기본 지식베이스와 사용자 업로드 문서를 **분리**하는 것이 핵심이다. 섞으면 다른 사용자의 업로드가 내 답변에 새어 들어간다.

---

## 5. 데이터

### 출처

온통청년(청년정책 통합정보) 개방 API에서 수집한 **청년정책 2,693건**.

### 파일

| 파일 | 내용 |
|---|---|
| `data/youth_policies_raw.json` | API 원본 응답 (2,693건) |
| `data/policies_structured.json` | 정규화 결과. 코드 필드에 사람이 읽는 이름(`*CdNm`)과 리스트(`*CdList`)를 덧붙임 |
| `data/policies_rag_docs.json` | 임베딩용 문서. `{plcyNo, text}` 형태로 정책 하나가 문서 하나 |
| `data/code_definitions.json` | 코드 → 한글명 매핑표 (`jobCd`, `schoolCd`, `earnCndSeCd` 등) |
| `data/policies_*.pdf` | 사람이 확인하기 위한 출력본 |

### 조건 매칭에 쓰는 필드

`UserProfile`은 사람이 읽는 값으로 받고, 검색 계층에서 코드로 변환해 필터링한다.

| UserProfile | 정책 필드 | 코드표 |
|---|---|---|
| `age` | `sprtTrgtMinAge` ~ `sprtTrgtMaxAge` | — (정수 범위) |
| `region` | `zipCdList` | 지역 코드 ↔ 행정구역 매핑 필요 |
| `employment` | `jobCdList` | `jobCd` — 재직자 / 미취업자 / 프리랜서 / (예비)창업자 … |
| `education` | `schoolCdList` | `schoolCd` — 고교 재학 / 대학 재학 / 대졸 예정 / 석·박사 … |
| `income_bracket` | `earnCndSeCd`, `earnMinAmt`, `earnMaxAmt` | `earnCndSeCd` — 무관 / 연소득 / 기타 |
| (확장) 혼인 | `mrgSttsCd` | `mrgSttsCd` |
| (확장) 전공 | `plcyMajorCdList` | `plcyMajorCd` |

정책 하나의 실제 모습:

```
plcyNm          [8월 접수] 2026년 구직청년 자격증 취득지원 사업
lclsfNm         교육･직업훈련        mclsfNm  교육비지원
sprtTrgtMinAge  19                  sprtTrgtMaxAge  39
jobCdNmList     ["제한없음"]         schoolCdNmList  ["제한없음"]
earnCndSeCdNm   무관
zipCdList       ["12210", "12240", "12270", "12300", "12330"]
aplyStartYmd    2026-08-03          aplyEndYmd  2026-08-31
operInstCdNm    전남광주통합특별시
aplyUrlAddr     https://youth.gwangju.go.kr/...
```

### 구현 시 주의

**"제한없음"을 반드시 통과시킬 것.** `jobCd`·`schoolCd`·`sbizCd`·`plcyMajorCd`에는 `제한없음` 코드(`0013010`, `0049010` 등)가 있고, 실제로 상당수 정책이 이 값을 쓴다. 필터 조건을 `사용자 값 == 정책 값` 으로만 짜면 이런 정책이 전부 탈락한다. **`사용자 값과 일치` OR `제한없음`** 으로 판정해야 한다.

**나이 제한 없는 정책**은 `sprtTrgtAgeLmtYn = 'N'` 으로 표시된다. 이 경우 나이 범위 비교를 건너뛴다.

**마감된 정책 처리** — `aplyPrdSeCd`가 `0057003`(마감)이거나 `aplyEndYmd`가 지난 정책은 기본적으로 제외하되, 사용자가 명시적으로 요청하면 보여준다. `0057002`는 상시 모집이라 기간 비교 대상이 아니다.

**지도 연동** — `zipCdList`의 지역 코드를 카카오맵 폴리곤(행정구역 GeoJSON)과 이어 붙일 매핑 테이블이 필요하다. 정책 하나가 여러 지역에 걸치므로 지역별 집계 시 중복 계산에 주의한다. `GET /api/regions/summary`가 이 집계를 담당한다.

**전국 단위 정책**은 `pvsnInstGroupCd`가 중앙부처인 경우가 많다. 지역 필터를 걸 때 "내 지역 + 전국"을 함께 잡아야 한다.

---

## 6. 프로젝트 구조

디렉터리 하나가 담당자 한 명에 대응한다. 소유자가 아닌 사람은 해당 디렉터리를 직접 수정하지 않고 Issue 또는 PR 리뷰로 요청한다.

```
team-13-project/
├── frontend/                        ← 이수민
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js               # /api 프록시 설정
│   ├── .env.example                 # VITE_* 환경변수
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                  # 라우터 · 레이아웃
│       ├── pages/
│       │   ├── ChatPage.jsx         # F1
│       │   ├── MapPage.jsx          # F3
│       │   └── DocumentsPage.jsx    # F2
│       ├── components/
│       │   ├── ChatWindow.jsx
│       │   ├── MessageBubble.jsx
│       │   ├── AttachMenu.jsx       # + 버튼 첨부 메뉴
│       │   ├── ProfilePanel.jsx     # 조건 입력
│       │   ├── SourceCard.jsx       # 출처 카드
│       │   ├── KakaoMap.jsx         # 지도 + 폴리곤
│       │   └── RegionPanel.jsx      # 슬라이드 패널
│       ├── hooks/
│       │   ├── useChatStream.js     # SSE 수신
│       │   ├── useProfile.js        # localStorage 영속화
│       │   └── useKakaoMap.js       # SDK 로드 · 이벤트
│       ├── api/
│       │   ├── client.js            # fetch 래퍼
│       │   └── mock.js              # MOCK 응답
│       └── styles/
│
├── src/
│   ├── backend/                     ← 최성호
│   │   ├── api.py                   # FastAPI 앱 · 라우터 등록 · StaticFiles 마운트
│   │   ├── routers/
│   │   │   ├── chat.py              # /api/ask, /api/ask/stream
│   │   │   ├── documents.py         # /api/documents
│   │   │   ├── policies.py          # /api/policies
│   │   │   └── vision.py            # /api/vision (P3)
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
│       ├── collect.py               # 온통청년 API 수집
│       ├── normalize.py             # 스키마 정규화 + 코드 해석
│       ├── indexer.py               # 청킹 → 임베딩 → Chroma 적재
│       ├── pdf.py                   # PDF 파싱 (표 포함)
│       └── vision.py                # 이미지 OCR (P3)
│
├── data/                            # §5 참고
├── chroma_db/                       # 벡터 DB (gitignore)
├── app.db                           # SQLite (gitignore)
├── tests/
├── docs/
│   └── presentation/                # 발표 자료
├── requirements.txt
├── Dockerfile.web                   # React 빌드 → nginx (Compose용)
├── Dockerfile.api                   # FastAPI (Compose용)
├── Dockerfile                       # multi-stage 통합 (HF Spaces용)
├── docker-compose.yml
├── .env.example
└── README.md
```

> `frontend/` 는 `npm` 생태계를 쓰므로 `src/` 밖에 둔다. Python 패키지 경로와 섞이지 않는다.

---

## 7. 역할 분담

**팀 구성: 4인 1팀**

| 이름 | 역할 | Module 13 | Module 14 | 소유 디렉터리 |
|---|---|---|---|---|
| **최성호** | 팀장 · Backend Engineer | 총괄·일정 관리 / FastAPI 서비스 · API 계약 설계 | Git 브랜치 전략 · PR 리뷰 운영 / `Dockerfile.api` | `src/backend/` |
| **박준혁** | AI Engineer (LLM · RAG) | 하이브리드 검색 / 프롬프트 설계 / 자격 진단 / 생성·스트리밍 | `docker-compose.yml` · 멀티 컨테이너 통합 | `src/rag/` |
| **김영민** | AI Engineer (Data · Ingest) | 정책 데이터 수집·정규화 / PDF 파싱 / 인덱싱 파이프라인 | HF Spaces 배포 · 통합 `Dockerfile` · CI/CD | `src/ingest/`, `data/` |
| **이수민** | Frontend Engineer | React SPA 전반 / 카카오맵 / 채팅 스트리밍 UI / 조건 입력 UX | `Dockerfile.web` · Docker Hub push | `frontend/` |

### 공동 책임

- **`src/backend/schemas.py`** — 최성호가 소유하되 변경은 반드시 PR + 전원 리뷰. 이 파일이 네 사람의 작업을 연결한다.
- **`requirements.txt`** — 각자 추가 시 PR로만. 버전을 고정(`==`)한다.
- **`frontend/package.json`** — 이수민이 소유. 다른 사람은 건드리지 않는다.
- **발표 자료** — 발표는 1인당 5분이므로 각자 자기 파트 슬라이드를 작성하고 최성호가 취합·통합한다.

### 업무량 분산 원칙

교수 자료의 기본안은 팀장에게 개발 롤을 두지 않는다(M13 총괄, M14 DevOps). 본 팀은 팀장이 Backend를 겸하므로, Module 14의 배포 작업(Git 20점 · Docker 20점 · Spaces 20점)을 한 사람에게 몰지 않고 아래와 같이 나눈다.

- Git 브랜치 전략 · PR · Issue 운영 → **최성호**
- Docker Compose 및 멀티 컨테이너 통합 → **박준혁**
- Hugging Face Spaces 배포 및 CI/CD → **김영민**
- 각자의 Dockerfile은 각자 작성 → **전원**

---

## 8. API 명세

모든 엔드포인트는 **`/api` 접두사**를 갖는다. 전체 명세는 서버 기동 후 `http://localhost:8000/docs` 에서 확인한다.

### 챗봇

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/api/ask` | `AskRequest` | `AskResponse` |
| `GET` | `/api/ask/stream` | `AskRequest` (query) | SSE 토큰 스트림 |
| `POST` | `/api/eligibility` | `UserProfile` | `EligibilityResponse` |

### 문서

| Method | Path | Request | Response |
|---|---|---|---|
| `POST` | `/api/documents` | `list[UploadFile]` | `list[DocumentResponse]` |
| `GET` | `/api/documents` | – | `list[DocumentResponse]` |
| `DELETE` | `/api/documents/{doc_id}` | – | `DeleteResponse` |

### 정책 · 지도

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/api/policies` | `region`, `category`, `page`, `size` | `PolicyListResponse` |
| `GET` | `/api/policies/{plcy_no}` | – | `PolicyDetail` |
| `GET` | `/api/regions/summary` | – | `list[RegionSummary]` (지역별 정책 수) |
| `GET` | `/api/codes` | – | `code_definitions.json` (프론트 셀렉트 박스용) |

### 세션 · 피드백

| Method | Path | Request | Response |
|---|---|---|---|
| `GET` | `/api/sessions/{sid}/messages` | – | `list[Message]` |
| `POST` | `/api/feedback` | `FeedbackRequest` | `OkResponse` |

### 주요 스키마

`UserProfile`은 사람이 읽는 값으로 받는다. 코드 변환은 `src/rag/retriever.py`에서 처리한다.

```python
class UserProfile(BaseModel):
    age: int | None = None
    region: str | None = None          # 시도 · 시군구
    employment: str | None = None      # jobCd 한글명 (예: "미취업자")
    education: str | None = None       # schoolCd 한글명 (예: "대학 재학")
    income_bracket: int | None = None  # 중위소득 %

class AskRequest(BaseModel):
    question: str
    session_id: str
    profile: UserProfile | None = None
    top_k: int = 5
    mode: SearchMode = SearchMode.HYBRID   # vector | bm25 | hybrid
    doc_ids: list[str] = []                # 세션 업로드 문서 한정 검색
    include_closed: bool = False           # 마감 정책 포함 여부

class Source(BaseModel):
    plcy_no: str        # 정책 고유번호
    title: str          # plcyNm
    organization: str   # operInstCdNm
    category: str       # lclsfNm · mclsfNm
    apply_url: str | None
    apply_period: str | None
    snippet: str
    score: float

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    matched_policies: list[str]   # plcyNo 목록
    session_id: str
    elapsed_ms: int
```

> `profile`이 `None`이거나 모든 필드가 비어 있으면 조건 필터 없이 전체 기준으로 검색한다.

---

## 9. 개발 순서

### Phase 0 — 합의와 골격 (전원 · 동시)

가장 중요한 단계다. **이 단계가 끝나야 네 사람이 병렬로 갈라질 수 있다.**

| # | 작업 | 담당 |
|---|---|---|
| 0-1 | 기능 우선순위 · 일정 확정, GitHub Issue 등록 | 최성호 |
| 0-2 | **`schemas.py` 확정 후 `main`에 선(先)머지** | 최성호 (전원 리뷰) |
| 0-3 | 디렉터리 골격 · `requirements.txt` · `.env.example` | 최성호 |
| 0-4 | ~~정책 데이터 수집~~ **완료** / 지역코드 ↔ 행정구역 매핑 확보 | 김영민 |
| 0-5 | 브랜치 보호 규칙 · PR 템플릿 · Issue 템플릿 | 최성호 |
| 0-6 | Vite 프로젝트 초기화 · 라우팅 · `api/mock.js` | 이수민 |

`0-6`은 프론트가 백엔드 완성을 기다리지 않게 하는 장치다. `VITE_USE_MOCK=true`면 `schemas.py` 형태의 가짜 응답을 반환하므로, 이수민은 UI를 끝까지 혼자 만들 수 있다.

### Phase 1 — 핵심 챗봇 (P0)

| 담당 | 작업 |
|---|---|
| 김영민 | `policies_rag_docs.json` → 청킹 → 임베딩 → Chroma 적재. 메타데이터로 나이·지역·직업·학력 코드 저장 |
| 박준혁 | 벡터 검색 + 프로필 메타 필터(§5 "제한없음" 규칙 포함) → 프롬프트 → 생성 |
| 최성호 | `POST /api/ask` · SQLite 대화 저장 · lifespan 모델 로딩 |
| 이수민 | 채팅 UI · 조건 입력 패널 · 출처 카드 · localStorage 프로필 유지 |

**Phase 1 종료 조건**: 조건을 넣고 뺐을 때 답이 달라지는 것이 눈으로 확인된다.

### Phase 2 — 문서 · 지도 (P1 · P2)

| 담당 | 작업 |
|---|---|
| 김영민 | 다중 PDF 파싱 · 표 추출 · 세션 임시 컬렉션 |
| 박준혁 | **하이브리드 검색**(BM25+Dense) · 프롬프트 개선 · 검색 성능 비교 실험 |
| 최성호 | `/api/documents` · `/api/policies` · `/api/regions/summary` · `/api/codes` · SSE |
| 이수민 | `+` 첨부 메뉴 · **카카오맵 컴포넌트** · SSE 수신 훅 · 검색모드 비교 UI |

### Phase 3 — 이미지 인식 (P3 · 조건부)

먼저 **기술 검증**부터 한다. 샘플 포스터 5장으로 OCR 정확도와 메모리 사용량을 측정하고, 팀 회의에서 진행 여부를 결정한다. 중단하기로 해도 검증 과정 자체를 발표에 포함한다.

| 담당 | 작업 |
|---|---|
| 김영민 | OCR 파이프라인 · 이미지 전처리 |
| 박준혁 | 추출 텍스트 → 정책 매칭 |
| 최성호 | `POST /api/vision` |
| 이수민 | 이미지 업로드 · 인식 결과 UI |

### Phase 4 — 배포 (Module 14)

이번 프로젝트는 **이미지를 두 가지로 만든다.** 이유는 아래 "단일 컨테이너 제약"을 참고한다.

| 담당 | 작업 |
|---|---|
| 이수민 | `Dockerfile.web` (node build → nginx) · Docker Hub push |
| 최성호 | `Dockerfile.api` · Docker Hub push · Git 히스토리 정리 |
| 박준혁 | `docker-compose.yml` · 서비스 간 네트워크 · 통합 테스트 |
| 김영민 | 통합 `Dockerfile` (multi-stage) · HF Spaces 배포 · CI/CD · 문제 해결 기록 |

#### 단일 컨테이너 제약

Hugging Face Docker Space는 **컨테이너를 하나만** 실행하고 포트도 하나만 연다. 따라서 배포 형태가 두 갈래로 나뉜다.

| | 로컬 · Compose | HF Spaces |
|---|---|---|
| 구성 | `web`(nginx) + `api`(uvicorn) 2컨테이너 | 단일 컨테이너 |
| 목적 | 서비스 분리 구조 시연 | 실제 배포 |
| 파일 | `docker-compose.yml` | `Dockerfile` (multi-stage) |

통합 `Dockerfile`은 node 스테이지에서 React를 빌드하고, python 스테이지로 `dist/`를 복사한 뒤 FastAPI가 서빙한다.

```dockerfile
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_KAKAO_MAP_KEY
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY --from=web /web/dist ./dist
EXPOSE 7860
CMD ["uvicorn", "src.backend.api:app", "--host", "0.0.0.0", "--port", "7860"]
```

**이 두 갈래가 갈라진 이유와 해결 과정이 Module 14 발표의 핵심 소재다.** 평가 기준에 *"배포 과정에서 발생하는 문제점의 해결 과정을 상세하게 기술할 것"* 이 명시되어 있다.

#### 그 밖의 배포 주의사항

**포트**: HF Docker Space 기본 포트는 `7860`이다. Space `README.md`의 `app_port`와 `Dockerfile`의 `EXPOSE`, uvicorn `--port` 를 모두 맞춘다.

**Vite 환경변수는 빌드 시점에 박힌다**: `VITE_*` 값은 런타임이 아니라 `npm run build` 시점에 번들에 포함된다. Docker에서는 `--build-arg` 로 넘겨야 하며, 배포 후 바꾸려면 다시 빌드해야 한다.

**카카오맵 키 노출**: JavaScript 키는 번들에 포함되어 브라우저에 노출된다. 이는 정상이며, 카카오 개발자 콘솔의 **도메인 등록**으로 보호한다. 비밀 키가 아니므로 별도 은닉이 필요 없다.

**저장소 용량**: `data/` 의 JSON·PDF가 이미 수십 MB다. Docker 이미지에 통째로 넣으면 빌드가 느려지므로, 인덱싱에 필요한 `policies_rag_docs.json`·`code_definitions.json` 만 복사하거나 미리 만든 `chroma_db/` 를 넣는 방안을 Phase 2 종료 전까지 결정한다.

---

## 10. Git 협업 규칙

Module 14 평가에 *"브랜치, 커밋, PR, Issue 등을 적절히 활용했는가"* 가 명시되어 있다. **`main`에 직접 push 하지 않는다.**

### 브랜치

```
main                    보호 브랜치. PR 병합으로만 갱신
 ├── feature/ui-chat
 ├── feature/ui-map
 ├── feature/api-ask
 ├── feature/rag-hybrid
 ├── feature/ingest-index
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
fix(rag): 제한없음 코드가 필터에서 탈락하던 문제 수정
chore(docker): 통합 이미지 포트를 7860으로 변경
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
- **`README.md` 는 여러 명이 동시에 고치기 쉬운 파일이다.** 수정 전 팀 채널에 알리고, 작업 중에는 `git pull` 을 자주 한다.
- `schemas.py` 변경은 반드시 팀 채널에 공지 후 PR. 계약이 바뀌면 네 명 모두 영향받는다.
- `package-lock.json` 은 커밋한다. 팀원 간 의존성 버전을 고정하기 위해서다.
- 작업 시작 전 `git switch main && git pull` 을 습관화한다.
- 하루가 끝나면 미완성이어도 push 한다. 로컬에만 쌓아두지 않는다.

---

## 11. 실행 방법

### 로컬

```bash
git clone https://github.com/knukdt14/team-13-project.git
cd team-13-project

# 백엔드
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # HF_TOKEN 등 입력

python -m src.ingest.indexer     # 최초 1회, 벡터 DB 구축
uvicorn src.backend.api:app --reload --port 8000     # 터미널 1

# 프론트엔드
cd frontend
npm install
cp .env.example .env             # VITE_KAKAO_MAP_KEY 입력
npm run dev                                          # 터미널 2
```

| 주소 | 설명 |
|---|---|
| http://localhost:5173 | 서비스 화면 (Vite 개발 서버) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |

### Docker

```bash
docker compose up --build              # web + api 2컨테이너
docker build -t youth-policy .         # HF Spaces용 통합 이미지
```

### 환경 변수

**백엔드** — `.env`

| 이름 | 설명 |
|---|---|
| `HF_TOKEN` | Hugging Face 토큰 |
| `CHROMA_DIR` | 벡터 DB 경로 (기본 `./chroma_db`) |
| `DB_PATH` | SQLite 경로 (기본 `./app.db`) |

**프론트엔드** — `frontend/.env` (모두 `VITE_` 접두사 필수, 빌드 시점에 주입)

| 이름 | 설명 |
|---|---|
| `VITE_KAKAO_MAP_KEY` | 카카오맵 JavaScript 키 |
| `VITE_API_BASE` | API 기본 경로 (기본 `/api`) |
| `VITE_USE_MOCK` | `true`면 백엔드 없이 가짜 응답으로 UI 개발 |

> **카카오맵 키 주의**: JavaScript 키는 카카오 개발자 콘솔에 **사용 도메인을 등록**해야 동작한다. 로컬(`http://localhost:5173`)과 배포 도메인(`https://<space>.hf.space`)을 모두 등록한다. Phase 2 시작 전에 미리 발급받아 둘 것.

---

## 12. 평가 기준 대응

### Module 13 (100점)

| 항목 | 배점 | 대응 |
|---|:---:|---|
| Frontend | 20 | 컴포넌트 설계, 커스텀 훅, React Router, **카카오맵 인터랙션**, `+` 파일 첨부, **SSE 스트리밍 렌더** |
| Backend / FastAPI | 20 | **Pydantic `response_model`**, `APIRouter`, `Depends`, `HTTPException`, `lifespan`, `StaticFiles` SPA 서빙, SSE |
| LLM / RAG | 20 | **하이브리드 검색**(BM25+Dense), **프로필 기반 코드 메타 필터**, 프롬프트 설계, 검색 모드별 성능 비교 |
| 발표 및 시연 | 20 | 디렉터리 = 담당자 구조, Issue·PR 히스토리로 협업 과정 증빙 |
| 프로젝트 완성도 | 20 | `frontend` / `backend` / `rag` / `ingest` 4계층 분리 |

### Module 14 (100점)

| 항목 | 배점 | 대응 |
|---|:---:|---|
| Git / GitHub | 20 | 보호된 `main`, `feature/*` 브랜치, Conventional Commits, PR 리뷰, Issue 연동 |
| Docker / Docker Hub | 20 | web·api 이미지 분리, **multi-stage build**, 레이어 캐시 최적화, Docker Hub 태그 관리 |
| Hugging Face Spaces | 20 | Docker SDK Space 배포, 단일 컨테이너 제약 대응, 포트 7860 전환, CI/CD |
| 발표 및 시연 | 20 | Compose 구조와 Spaces 단일 컨테이너 사이의 간극을 어떻게 해결했는지 기록 |
| 프로젝트 완성도 | 20 | Compose 기반 멀티 컨테이너 통합 동작 |

### "수업에서 다루지 않은 것" 대조표

두 모듈 모두 만점 조건이 *기존 수업에서 다루지 않은 요소의 추가*다.

| 영역 | 수업 범위 (기본점) | 본 프로젝트 추가분 |
|---|---|---|
| Frontend | Streamlit 위젯 · `session_state` · `file_uploader` · Flask + Jinja2 템플릿 | **React 컴포넌트 설계** · 커스텀 훅 · 클라이언트 라우팅 · **SSE 스트리밍 렌더** · localStorage · CSS 트랜지션 · **카카오맵 SDK 연동** · Vite 빌드 |
| Backend | `Form(...)` · 생 `dict` 반환 · `UploadFile` · `StreamingResponse` | **Pydantic 모델 · `response_model`** · `APIRouter` · `Depends` · `lifespan` · `StaticFiles` SPA 서빙 · SSE |
| RAG | `PyPDFLoader` · `RecursiveCharacterTextSplitter` · `similarity_search(k=3)` | **하이브리드 검색** · **코드 기반 메타데이터 필터** · 표 파싱 · 다중 문서 · 검색 성능 비교 |
| Data | 단일 PDF 로드 | **개방 API 수집 2,693건** · 코드 정규화 · SQLite 이력 관리 · 세션별 컬렉션 분리 |
| DevOps | 단일 스테이지 Dockerfile · 단일 서비스 | **multi-stage build** · Compose 멀티 컨테이너 · 단일 컨테이너 제약 대응 |

---

## 13. 팀

| 이름 | 역할 | GitHub |
|---|---|---|
| 최성호 | 팀장 · Backend Engineer | |
| 박준혁 | AI Engineer (LLM · RAG) | |
| 김영민 | AI Engineer (Data · Ingest) | |
| 이수민 | Frontend Engineer | |

경북대학교 AI·BigData 전문가 양성과정 KDT 14기 · Module 13 & 14 미니 프로젝트
지도: 배준현 교수 (경북대학교)