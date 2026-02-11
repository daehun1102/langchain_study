# Human-in-the-Loop 반도체 공정 에이전트

LangGraph의 `interrupt()` 기반 Human-in-the-Loop 패턴을 구현한 반도체 공정 검사 에이전트 시스템.

## 사전 요구사항

- Python 3.11+
- Node.js 18+
- OpenAI API Key

## 환경 변수 설정

```bash
# .env 또는 터미널에서 직접 설정
export OPENAI_API_KEY="sk-..."
```

Windows (PowerShell):
```powershell
$env:OPENAI_API_KEY="sk-..."
```

## 백엔드 실행 (FastAPI + Uvicorn, 포트 2024)

```bash
# 프로젝트 루트에서
cd human_in_the_loop

# 가상환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 의존성 설치 (최초 1회)
pip install fastapi uvicorn langchain langgraph langchain-openai

# ai_server 디렉토리로 이동 후 uvicorn 실행
cd ai_server
uvicorn main:app --host 0.0.0.0 --port 2024 --reload
```

서버가 `http://localhost:2024` 에서 실행됩니다.

헬스체크: `GET http://localhost:2024/ok`

## 프론트엔드 실행 (Vite + Vue, 포트 5173)

```bash
# 새 터미널에서
cd human_in_the_loop/frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 `http://localhost:5173` 접속.

> Vite 프록시가 `/threads`, `/assistants`, `/ok` 요청을 백엔드(2024)로 자동 전달합니다.

## 사용 방법

1. 프론트엔드에서 Thread를 생성하고 서버에 연결합니다.
2. 메시지를 입력합니다. 예: `LOT-2024001 Photo 공정 검사해줘`
3. 에이전트가 이력을 조회한 뒤, 라우터 에이전트 호출 전 **승인 카드**가 표시됩니다.
4. 세 가지 액션 중 선택:
   - **승인** : 요청 그대로 공정 에이전트에 전달
   - **거부** : 사유 입력 후 요청 거절
   - **수정** : 파라미터 수정 후 실행

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/threads` | 새 Thread 생성 |
| GET | `/threads/{thread_id}/state` | Thread 상태 조회 |
| POST | `/threads/{thread_id}/runs/stream` | SSE 스트리밍 실행/Resume |
| POST | `/assistants/search` | Assistant 목록 조회 |
| GET | `/ok` | 헬스체크 |
