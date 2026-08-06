# 청년정책도우미

> 경북대학교 AI·BigData 전문가 양성과정 KDT 14기 웹 프로젝트 3팀

흩어진 청년정책을 사용자 조건에 맞게 찾아주고, 어려운 공고문을 쉬운 말로 설명하는
RAG 기반 정책 탐색 서비스입니다.

온통청년 개방 API에서 수집한 **청년정책 2,698건**을 대상으로 나이·지역·취업상태·학력
조건을 먼저 적용한 뒤 FAISS와 BM25로 검색합니다. 답변에는 참고한 정책을 함께 표시해
사용자가 근거를 직접 확인할 수 있습니다.

2026년 8월 6일 기준 신청 가능한 정책은 **707건(26%)**입니다.

---

## 핵심 기능

- **맞춤 정책 상담** — 사용자 조건을 반영한 RAG 검색과 SSE 답변 스트리밍
- **근거 정책 확인** — 답변에 사용한 정책을 분야별 색상 카드로 제공
- **정책 직접 신청** — 신청 주소가 확인된 정책 204건을 마감 임박순으로 안내
- **지역별 탐색** — 카카오맵 시도 폴리곤을 이용한 지역 정책 조회
- **정책 목록** — 분야·키워드·조건 필터, 정렬, 페이지네이션
- **공고문 첨부** — PDF 텍스트 추출과 EasyOCR 이미지 인식
- **대화 저장** — SQLite에 대화 이력·첨부 메타데이터·피드백 저장

### 화면 구성

| 경로 | 화면 | 주요 기능 |
|---|---|---|
| `/` | 홈 | 정책 검색, 인기 정책, 주요 기능 진입 |
| `/chat` | 정책 상담 | RAG 챗봇, 출처 확인, 파일 첨부 |
| `/apply` | 바로 신청 | 신청 가능한 정책과 외부 신청 페이지 연결 |
| `/map` | 지역별 탐색 | 시도별 정책 수와 지역 정책 조회 |
| `/documents` | 정책 목록 | 분야·키워드·조건 검색과 페이지네이션 |

홈에서 입력한 질문은 상담 화면으로 이어집니다. 기능 화면의 조건은
`localStorage`에 저장되어 화면을 이동해도 유지됩니다.

---

## 시스템 구조

```text
브라우저
   │
   ▼
web · React + nginx (:5173)
   │  /api 프록시 · SSE
   ▼
api · FastAPI + SQLite (:8000)
   │  HTTP
   ▼
ai · FAISS + BM25 + BGE-M3 + Solar + EasyOCR (:9000)
```

서비스는 역할에 따라 세 컨테이너로 분리했습니다.

- `web` — React 빌드 결과를 nginx로 제공하고 `/api`를 백엔드로 전달합니다.
- `api` — 정책 목록·지도·자격 판정·대화 저장을 담당합니다. AI 모델을 적재하지 않습니다.
- `ai` — 임베딩 검색·답변 생성·OCR처럼 모델이 필요한 작업만 담당합니다.

AI 모델을 읽는 동안에도 정책 목록과 지도는 바로 사용할 수 있습니다. BGE-M3 모델은
AI 컨테이너의 첫 실행 때 내려받고 Docker 볼륨에 캐시합니다.

---

## 실행 방법

### Docker Compose

**1. 키를 넣습니다.** 루트 `.env.example` 을 `.env` 로 복사해 두 값을 채웁니다.

```bash
cp .env.example .env
```

```env
UPSTAGE_API_KEY=up_...          # Upstage 콘솔에서 발급
VITE_KAKAO_MAP_KEY=...          # 카카오 개발자 콘솔 JavaScript 키
```

> **반드시 루트 `.env` 에 넣습니다.** 로컬 실행은 `src/rag/.env` 와
> `frontend/.env` 를 읽지만, 컨테이너에는 그 파일들이 들어가지 않습니다
> (`.dockerignore` 가 `**/.env` 를 막습니다). compose 는 루트 `.env` 만
> 읽습니다. 여기를 비워 두면 **로컬에서는 되는데 컨테이너에서만** 챗봇이나
> 지도가 동작하지 않습니다.

**2. 띄웁니다.**

```bash
docker compose up --build
```

첫 빌드는 torch 설치 때문에 오래 걸립니다. 이미지 세 개가 만들어집니다.

```text
youth-policy-web     80.4MB
youth-policy-api      254MB
youth-policy-ai      2.47GB
```

**3. 상태를 확인합니다.** `ai` 는 임베딩 모델(약 2GB)을 내려받으므로 늦게
준비됩니다. CPU 기준 약 3분입니다.

```bash
docker compose ps          # 세 컨테이너가 healthy 가 될 때까지
curl http://localhost:8000/api/health
```

`rag_mode` 가 `ready` 면 챗봇까지 사용할 수 있습니다. `unavailable` 이어도
정책 목록·지도·바로 신청은 정상 동작합니다.

**4. 접속합니다.** http://localhost:5173

**끝낼 때는** `docker compose down` 을 실행합니다. 그러지 않으면 포트
5173·8000·9000 을 컨테이너가 계속 잡고 있어 로컬 개발 서버가 뜨지 않습니다.

#### 자주 겪는 문제

| 증상 | 원인과 해결 |
|---|---|
| 챗봇만 답을 못 함 | `UPSTAGE_API_KEY` 누락. `generator_ready: false` 를 확인하고 루트 `.env` 에 넣은 뒤 다시 띄웁니다 |
| 지도만 빈 화면 | `VITE_*` 는 빌드 시점에 번들에 박힙니다. 키를 넣은 뒤 `docker compose build web` 으로 다시 빌드해야 반영됩니다 |
| 지도가 "도메인 확인" 오류 | 접속 중인 주소를 카카오 개발자 콘솔 사이트 도메인에 등록합니다 |

### 로컬 개발

```bash
pip install -r requirements.txt

# 터미널 1 — AI 서비스
uvicorn src.ai.main:app --port 9000

# 터미널 2 — 백엔드
uvicorn src.backend.main:app --port 8000

# 터미널 3 — 프론트엔드
cd frontend
npm install
npm run dev
```

로컬 실행에서는 Solar 키를 `src/rag/.env`, 카카오맵 키를 `frontend/.env`에 둡니다.
Docker Compose는 루트 `.env`를 사용합니다. 실제 `.env` 파일은 저장소에 포함하지
않습니다.

### GitHub Codespaces

`.devcontainer/devcontainer.json` 에 Python 3.12, Node 20, Docker 환경과 포트
5173·8000·9000 설정이 들어 있습니다.

**1. 코드스페이스를 만듭니다.** 저장소에서 **Code → Codespaces →
Create codespace on main**.

준비되면 `requirements.txt` 와 `npm install` 이 자동으로 실행됩니다. torch·
sentence-transformers·EasyOCR 을 받으므로 첫 생성은 오래 걸립니다. **시연
당일에 처음 만들지 말고 미리 한 번 띄워 두기 바랍니다.**

**2. 키를 넣습니다.** 코드스페이스에는 `.env` 가 없습니다(저장소에 포함하지
않습니다). 두 파일을 직접 만듭니다.

```bash
printf 'UPSTAGE_API_KEY=up_...\n' > src/rag/.env
printf 'VITE_KAKAO_MAP_KEY=...\n' > frontend/.env
```

**3. 카카오 도메인을 등록합니다.** 이 단계를 건너뛰면 지도만 빈 화면이 됩니다.

코드스페이스는 포트를 아래 형식으로 엽니다. 코드스페이스를 새로 만들 때마다
주소가 바뀌므로 그때마다 등록해야 합니다.

```text
https://<codespace-name>-5173.app.github.dev
```

VS Code 아래 **PORTS 탭**에서 5173 의 주소를 복사해 카카오 개발자 콘솔의
사이트 도메인에 추가합니다. 다른 사람에게 보여주려면 같은 탭에서 5173 의
**Visibility 를 Public** 으로 바꿉니다.

**4. 터미널 세 개로 서비스를 띄웁니다.** 순서가 있습니다.

```bash
uvicorn src.ai.main:app --port 9000        # 모델을 읽습니다. 먼저 띄웁니다
uvicorn src.backend.main:app --port 8000
cd frontend && npm run dev
```

5173 이 자동으로 브라우저에서 열립니다.

> 무료 티어는 2코어·CPU 전용입니다. BGE-M3 첫 적재와 답변 생성이 로컬보다
> 느립니다. `docker compose` 를 코드스페이스 안에서 빌드하면 훨씬 오래
> 걸리므로, 시연에는 위처럼 직접 띄우는 편을 권합니다. 컨테이너 구성을 보여줘야
> 할 때만 `docker compose up --build` 를 사용합니다(docker-in-docker 가
> 켜져 있습니다).

---

## 검색과 답변 흐름

```text
질문과 사용자 조건
   │
   ├─ 조건 선필터: 나이 · 지역 · 취업상태 · 학력 · 소득 · 마감 여부
   ▼
FAISS 벡터 검색 + BM25 키워드 검색
   │
   ▼
상위 정책과 최근 대화 6턴을 Solar에 전달
   │
   ▼
SSE 답변 스트리밍 + 근거 정책 카드
```

검색 전에 조건을 적용하기 때문에 사용자에게 해당하지 않는 정책이 답변 근거에 섞이는
문제를 줄였습니다. 사이드바에서 직접 선택한 조건은 질문에서 자동으로 읽은 조건보다
우선합니다.

첨부한 PDF와 이미지는 내용을 쉽게 설명하는 데 사용합니다. 공고문에서 자격 조건을
자동 추출해 합격 여부를 판정하는 기능은 실험 정확도가 낮아 포함하지 않았습니다.

---

## 주요 API

모든 사용자용 API는 `/api`로 시작하며 Pydantic 응답 모델을 사용합니다.

| 구분 | Method | Path | 설명 |
|---|---|---|---|
| 상담 | `POST` | `/api/ask` | 비스트리밍 답변 |
| 상담 | `GET` | `/api/ask/stream` | SSE 스트리밍 답변 |
| 판정 | `POST` | `/api/eligibility` | 모델을 사용하지 않는 조건 판정 |
| 정책 | `GET` | `/api/policies` | 정책 검색·필터·정렬·페이지네이션 |
| 정책 | `GET` | `/api/policies/{plcy_no}` | 정책 상세 |
| 지역 | `GET` | `/api/regions/summary` | 시도별 정책 수 |
| 지역 | `GET` | `/api/geo/provinces` | 시도 경계 GeoJSON |
| 첨부 | `POST` | `/api/documents` | PDF·이미지 업로드 |
| 첨부 | `GET` | `/api/documents` | 세션 첨부 목록 |
| 첨부 | `DELETE` | `/api/documents/{doc_id}` | 첨부 삭제 |
| 세션 | `GET` | `/api/sessions/{sid}/messages` | 대화 이력 |
| 기타 | `GET` | `/api/meta` | 필터 선택지 |
| 기타 | `GET` | `/api/health` | 서비스 상태 |

AI 서비스의 `/search`, `/generate`, `/interpret`, `/ocr`는 백엔드가 내부 통신에
사용합니다. 프론트엔드는 이 API를 직접 호출하지 않습니다.

---

## 프로젝트 구조

```text
team-13-project/
├── frontend/               React + Vite 프론트엔드
│   └── src/
│       ├── pages/          홈 · 상담 · 바로 신청 · 지도 · 정책 목록
│       ├── components/     레이아웃 · 조건 · 채팅 · 지도 · 정책 카드
│       ├── hooks/          조건 · 스트리밍 · 첨부 · 지도 상태
│       ├── api/            API 클라이언트
│       └── styles/         디자인 토큰과 화면 스타일
├── src/
│   ├── backend/            FastAPI 라우터 · 스키마 · 서비스 · SQLite
│   ├── ai/                 검색 · 생성 · OCR 내부 API
│   ├── rag/                FAISS/BM25 검색 · 필터 · 생성 · 인덱스
│   ├── ingest/             수집 · 정규화 · 요약 · 문서 처리
│   └── shared/             공용 상수와 경로
├── data/                   정책 데이터와 코드 정의
├── Dockerfile.web
├── Dockerfile.api
├── Dockerfile.ai
└── docker-compose.yml
```

---

## 데이터 처리 원칙

정책 데이터의 실제 형식에 맞춰 다음 규칙을 적용합니다.

- `sprtTrgtAgeLmtYn`은 이름과 반대로 `Y`가 "나이 제한 없음"입니다. 다만 제한이
  없더라도 이 서비스가 다루는 청년 범위(15~49세)는 적용합니다. 그렇지 않으면
  13세에게도 제한 없는 정책이 전부 걸립니다.
- 청년 범위를 청년기본법(19~34세)이 아니라 **15~49세**로 잡은 것은 데이터
  때문입니다. 나이를 명시한 정책의 상한이 39세(890건)·45세(158건)·49세(75건)로
  퍼져 있어, 39세로 막으면 40대에게 233건이 보이지 않습니다. 접수 중 기준으로
  **39세는 681건, 40세는 53건**까지 떨어집니다. 값은
  `src/shared/constants.py` 한 곳에 두고 백엔드와 RAG가 함께 씁니다.
- 직업·학력 조건의 `제한없음`은 모든 사용자에게 통과시킵니다.
- 지역을 선택하면 전국 정책은 기본적으로 제외하고 사용자가 포함 여부를 선택합니다.
- 마감 상태이거나 종료일이 지난 정책은 기본 검색에서 제외합니다.
- 카테고리는 키워드가 아닌 대분류 필드를 기준으로 묶습니다.
- 기관이 작성한 제출 서류는 임의로 요약하거나 생성하지 않습니다.
- 조회수는 서비스 실시간 조회수가 아니라 수집 당시 온통청년 누적 조회수입니다.

2026년 8월 6일 기준 접수 중인 정책의 주요 분포는 다음과 같습니다.

```text
전체 2,698건 · 접수 중 707건 · 마감 1,991건
일자리 234 · 금융복지문화 200 · 교육 101 · 주거 89 · 참여 82
상시 446 · 31일 이상 245 · 30일 이내 16
신청 URL 확인 204 · 제출 서류 확인 208 · 사전 요약 355
```

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React, Vite, React Router, Kakao Maps JavaScript SDK |
| Backend | FastAPI, Pydantic, SQLite, SSE |
| Search | FAISS, BM25, BGE-M3 |
| Generation | Upstage Solar |
| Documents | pypdf, EasyOCR |
| Deployment | Docker, Docker Compose, nginx, GitHub Codespaces |

---

## 검증

```bash
python -m unittest discover -s src/rag/tests -t .
cd frontend && npm run build
```

- RAG 단위 테스트 **32개 통과**
- 프론트엔드 프로덕션 빌드 통과

### 컨테이너 배포 검증

`docker compose build` 와 `up` 을 실제로 실행해 확인했습니다.

```text
youth-policy-web     80.4MB
youth-policy-api      254MB     모델을 적재하지 않아 가볍습니다
youth-policy-ai      2.47GB

세 컨테이너 healthy · rag_mode: ready
FAISS + BGE-M3 를 CPU 에서 약 3분 만에 적재
챗봇 스트리밍 234토큰 · 첫 토큰 3.3초 · 전체 4.6초
브라우저 → web(nginx) → api → ai 전 구간 통과
```

AI가 모델을 읽는 3분 동안에도 정책 목록·카테고리 필터·인기순 정렬·지역 요약이
정상 동작했습니다. 컨테이너를 역할별로 나눈 설계가 실제로 작동합니다.

---

## 알려진 한계

- 정책 데이터는 스냅샷이므로 새 정책은 데이터를 다시 수집한 뒤 반영됩니다.
- 일부 지역은 현재 신청 가능한 지역 전용 정책이 없을 수 있습니다.
- 제출 서류는 원본 데이터에 내용이 있는 정책만 표시합니다.
- 첨부 공고문은 쉽게 설명하지만 자격 여부를 자동 판정하지 않습니다.
- 실제 신청 전에는 반드시 해당 기관의 최신 공고문을 확인해야 합니다.

---

## 팀

| 담당 | 영역 |
|---|---|
| 최성호 | Backend · API · SQLite · 컨테이너 구조 |
| 박준혁 | RAG · 하이브리드 검색 · 생성 |
| 김영민 | 데이터 수집 · 정규화 · 문서 처리 |
| 이수민 | Frontend · 지도 · UI/UX |

경북대학교 KDT 14기 웹 프로젝트 3팀
