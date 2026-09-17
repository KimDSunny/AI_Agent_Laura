# PLANET Laura

신입사원이 회사와 업무 환경을 빠르게 이해할 수 있도록 돕는 사내 온보딩 AI Agent입니다.

Laura는 사내 문서를 근거로 질문에 답하고, 사용자의 승인을 받은 뒤 Google Calendar 일정 등록이나 온보딩 체크리스트 변경 같은 실제 작업을 수행합니다. 팀 채팅은 AI 응답과 분리되어 팀원 간 대화 공간으로 동작합니다.

## 주요 기능

### 사내 문서 RAG

- 회사 소개와 연혁, 조직도, 담당 업무 검색
- 현재 프로젝트와 팀별 주간 계획 안내
- 복지·사내 규정, 개발 환경, 휴가·결재 절차 안내
- 검색 결과 재정렬과 팀별 접근 권한 확인
- 근거가 없는 질문에는 `확인할 수 없습니다`로 응답
- 답변 하단에 출처 문서명 표시

### AI Agent와 Tool Calling

LangGraph가 질문의 의도를 판단하고 필요한 도구를 선택합니다.

| 도구 | 기능 | 실행 방식 |
| --- | --- | --- |
| `search_company_documents` | 사내 문서 검색 | 즉시 실행 |
| `find_employee` | 임직원 소속 조회 | 즉시 실행 |
| `get_onboarding_progress` | 온보딩 진행률 조회 | 즉시 실행 |
| `get_current_projects` | 현재 프로젝트 조회 | 즉시 실행 |
| `update_checklist` | 체크리스트 상태 변경 | 사용자 승인 후 실행 |
| `create_schedule` | Google Calendar 일정 생성 | 사용자 승인 후 실행 |

- 도구 호출 실패 시 한 번 자동 재시도
- 일정 정보 등이 부족하면 필요한 내용만 재질문
- 변경 작업은 승인 전까지 실행하지 않음

### Google Calendar 연동

- 대화에서 일정 제목과 날짜·시간을 파악
- 사용자 승인 후 실제 Google Calendar에 일정 생성
- OAuth 갱신 토큰을 서버에서 암호화하여 저장
- 생성된 Google 이벤트 ID와 링크를 감사 기록으로 보관

### 온보딩과 팀 채팅

- 신입사원 소개 및 초기 프로필 설정
- Laura 전용 AI 대화방
- 부서별 팀원 그룹 채팅
- 멀티 Agent 오케스트레이션 콘셉트 데모

## 기술 스택

- Frontend: React, Vite
- Backend: FastAPI, Python 3.12, Uvicorn
- AI: OpenAI Responses API, LangGraph
- Database: Supabase PostgreSQL, pgvector, Row Level Security
- Authentication: Supabase Anonymous Auth, HttpOnly 세션 쿠키
- Integration: Google Calendar API, OAuth 2.0
- Test: Pytest

## 아키텍처

```text
React + Vite
     │  REST / SSE
     ▼
FastAPI ── LangGraph ── OpenAI Responses API
   │  ├── 사내 문서 검색
   │  ├── 승인 기반 Agent Action
   │  └── Google Calendar API
   ▼
Supabase PostgreSQL + pgvector + RLS
```

## 프로젝트 구조

```text
.
├── src/                     # React 애플리케이션
│   ├── components/          # 온보딩, 채팅, 승인 UI
│   └── services/            # FastAPI 통신 모듈
├── public/assets/           # 이미지와 오디오 리소스
├── backend/
│   ├── app/
│   │   ├── api/routes/      # API 엔드포인트
│   │   ├── models/          # 요청·응답 모델
│   │   └── services/        # Agent, RAG, Calendar 서비스
│   ├── scripts/             # 문서 재색인 및 검증 도구
│   └── tests/               # 백엔드 테스트
├── company-documents/       # PLANET 사내 mock 문서
└── supabase/migrations/     # 스키마, RLS, 문서 데이터 마이그레이션
```

## 로컬 실행

### 사전 준비

- Node.js 20 이상
- Python 3.12 이상
- [uv](https://docs.astral.sh/uv/)
- Supabase 프로젝트
- OpenAI API 키
- Google Calendar 기능을 사용할 경우 Google Cloud OAuth 클라이언트

### 1. 저장소 복제 및 프론트엔드 설치

```bash
git clone https://github.com/KimDSunny/planet-laura.git
cd planet
npm install
```

### 2. 백엔드 환경변수 설정

```bash
cp backend/.env.example backend/.env
```

`backend/.env`에 아래 값을 입력합니다.

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/api/v1/integrations/google-calendar/callback
GOOGLE_OAUTH_STATE_SECRET=
GOOGLE_TOKEN_ENCRYPTION_KEY=
FRONTEND_URL=http://127.0.0.1:5173
```

비밀키 생성 예시:

```bash
openssl rand -hex 32
cd backend
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

첫 번째 값은 `GOOGLE_OAUTH_STATE_SECRET`, 두 번째 값은 `GOOGLE_TOKEN_ENCRYPTION_KEY`에 사용합니다.

> `SUPABASE_SECRET_KEY`, `OPENAI_API_KEY`, Google OAuth 비밀값은 프론트엔드 코드나 Git 저장소에 커밋하지 마세요.

### 3. Supabase 설정

Supabase Dashboard에서 다음 설정을 확인합니다.

1. `Authentication → Sign In / Providers`에서 Anonymous Sign-In을 활성화합니다.
2. `supabase/migrations/`의 마이그레이션을 순서대로 적용합니다.
3. pgvector 확장과 RLS 정책이 정상적으로 생성됐는지 확인합니다.

Supabase CLI를 연결한 환경에서는 다음 명령으로 적용할 수 있습니다.

```bash
supabase db push
```

### 4. 백엔드 실행

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API: `http://127.0.0.1:8000`
- Swagger 문서: `http://127.0.0.1:8000/docs`

### 5. 프론트엔드 실행

새 터미널에서 실행합니다.

```bash
npm run dev
```

브라우저에서 `http://127.0.0.1:5173`에 접속합니다. 개발 서버는 `/api` 요청을 FastAPI로 프록시합니다.

## Google Calendar OAuth 설정

Google Cloud Console에서 Calendar API를 활성화하고 `웹 애플리케이션` 유형의 OAuth 클라이언트를 생성합니다.

로컬 개발용 승인된 리디렉션 URI:

```text
http://127.0.0.1:8000/api/v1/integrations/google-calendar/callback
```

쿠키와 OAuth 콜백의 호스트가 일치해야 하므로 로컬에서는 `localhost`와 `127.0.0.1`을 섞어 사용하지 않는 것이 좋습니다. 운영 배포 시에는 `GOOGLE_OAUTH_REDIRECT_URI`, `FRONTEND_URL`, Google Cloud Console의 승인된 URI를 실제 HTTPS 주소로 함께 변경해야 합니다.

## 테스트

백엔드 테스트:

```bash
npm run test:api
```

프론트엔드 프로덕션 빌드:

```bash
npm run build
```

회사 문서를 변경한 뒤에는 문장과 임베딩을 다시 동기화합니다.

```bash
cd backend
uv run python scripts/reindex_company_documents.py
uv run python scripts/verify_company_rag.py
```

## Docker로 로컬 실행

React 프로덕션 빌드와 FastAPI를 하나의 이미지로 빌드합니다.

```bash
docker build -t planet-laura .
```

로컬 환경변수를 컨테이너에 전달해 실행합니다.

```bash
docker run --rm \
  --name planet-laura \
  --env-file backend/.env \
  -e FRONTEND_URL=http://127.0.0.1:8000 \
  -p 8000:8000 \
  planet-laura
```

- 애플리케이션: `http://127.0.0.1:8000`
- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/api/v1/health`

이미 `8000` 포트를 사용하는 컨테이너나 로컬 서버가 있다면 먼저 종료합니다.

```bash
docker ps
docker stop <container-name-or-id>
```

## 데이터와 보안

- 브라우저별 익명 Supabase 사용자를 생성하고 세션은 HttpOnly 쿠키에 저장합니다.
- 사용자 데이터는 PostgreSQL RLS로 분리합니다.
- Google OAuth 토큰은 브라우저에 전달하지 않고 서버에서 암호화합니다.
- 회사 문서 답변은 검색된 근거만 사용합니다.
- 일정과 체크리스트 같은 변경 작업은 사용자 승인 후 실행합니다.
- `.env`와 로컬 OAuth 설정 파일은 `.gitignore`에 포함되어 있습니다.

## 배포 계획

Docker 이미지 하나에 React 프로덕션 빌드와 FastAPI를 구성하고 다음 흐름으로 AWS에 배포할 예정입니다.

```text
GitHub → GitHub Actions → Amazon ECR → AWS App Runner
```

배포 환경에서는 모든 비밀값을 저장소가 아닌 AWS 환경변수 또는 Secrets Manager로 관리해야 합니다.

## 문서 데이터 안내

`company-documents/`의 회사·조직·프로젝트 정보는 제품 데모를 위해 만든 mock 데이터입니다. 실제 운영 환경에서는 사내 권한 정책과 문서 갱신 절차를 적용해야 합니다.
