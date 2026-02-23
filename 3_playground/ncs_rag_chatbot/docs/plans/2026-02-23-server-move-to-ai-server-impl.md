# server.py → ai_server/ 이동 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `server.py`를 `ai_server/server.py`로 이동하고, `sys.path` 해킹 및 미사용 파일을 제거한다.

**Architecture:** `server.py`를 `ai_server/`로 git mv하면, uvicorn을 `ai_server/` 내에서 실행하게 되어 Python이 CWD를 자동으로 sys.path에 추가한다. 기존 flat import는 그대로 유지되며, eval/ 시스템의 실행 패턴과 일관성이 생긴다.

**Tech Stack:** Python, FastAPI, uvicorn, git

---

### Task 1: server.py를 ai_server/로 이동

**Files:**
- Delete: `server.py` (git mv로 이동)
- Create: `ai_server/server.py` (git mv 결과)

**Step 1: git mv 실행**

```bash
cd C:/study/langchain_study/3_playground/ncs_rag_chatbot
git mv server.py ai_server/server.py
```

Expected: 오류 없음. `git status`에서 `renamed: server.py -> ai_server/server.py` 확인.

**Step 2: git status로 확인**

```bash
git status
```

Expected 출력:
```
Changes to be committed:
  renamed:    server.py -> ai_server/server.py
```

---

### Task 2: sys.path 해킹 제거

**Files:**
- Modify: `ai_server/server.py:22` — sys.path.insert 줄 삭제

**Step 1: 대상 줄 확인**

`ai_server/server.py` 15~25번 줄을 확인한다:
```python
import sys
import os
...
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai_server"))
```
이 `sys.path.insert` 줄이 삭제 대상이다.

**Step 2: sys.path.insert 줄 삭제**

`ai_server/server.py`에서 아래 줄을 삭제한다:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai_server"))
```

삭제 후, 바로 아래 줄인 `# 트레이싱은 LangChain import보다 먼저 초기화해야 모든 호출을 계측한다` 코멘트가 이어져야 한다.

**Step 3: docstring 실행 명령 업데이트**

`ai_server/server.py` 맨 위 docstring에서:
```python
# 실행: uvicorn server:app --reload --port 8000
```
를 찾아 아래로 교체한다:
```python
# 실행 (ai_server/ 디렉토리에서): uvicorn server:app --reload --port 8000
```

---

### Task 3: 미사용 main.py 삭제

**Files:**
- Delete: `ai_server/main.py`

**Step 1: main.py 내용 확인 (삭제 전 최종 확인)**

```bash
cat ai_server/main.py
```

테스트/실험용 코드이며 server.py가 import하지 않음을 확인한다.

**Step 2: git rm으로 삭제**

```bash
git rm ai_server/main.py
```

Expected: `rm 'ai_server/main.py'`

---

### Task 4: README.md 업데이트

**Files:**
- Modify: `README.md` — 3곳 수정

**수정 1: pip install 명령**

찾기:
```
pip install -r requirements.txt
```
교체:
```
pip install -r ai_server/requirements.txt
```

**수정 2: Python AI 서버 실행 명령 (실행 방법 섹션)**

찾기:
```bash
# 3. Python AI 서버
source venv/Scripts/activate   # Windows: venv\Scripts\activate
uvicorn server:app --reload --port 8000
```
교체:
```bash
# 3. Python AI 서버
source venv/Scripts/activate   # Windows: venv\Scripts\activate
cd ai_server
uvicorn server:app --reload --port 8000
```

**수정 3: 프로젝트 구조 다이어그램**

찾기:
```
├── server.py                       # FastAPI 앱 진입점
├── requirements.txt                # Python 의존성
```
교체 (server.py 줄 삭제, requirements.txt 줄 삭제, ai_server 블록에 server.py 추가):

기존 ai_server 블록:
```
├── ai_server/                      # Python AI 서버
│   ├── agent.py                    # LangGraph ReAct Agent
```
교체:
```
├── ai_server/                      # Python AI 서버
│   ├── server.py                   # FastAPI 앱 진입점
│   ├── requirements.txt            # Python 의존성
│   ├── agent.py                    # LangGraph ReAct Agent
```

---

### Task 5: 동작 검증

**Step 1: import 의존성 확인**

`ai_server/server.py`에서 import하는 모듈들이 모두 `ai_server/`에 존재하는지 확인한다:

```bash
ls ai_server/*.py
```

Expected: `agent.py`, `embeddings.py`, `vector_store.py`, `tool.py`, `ingest.py`, `tracing.py`, `server.py` 모두 존재.

**Step 2: Python syntax 검증**

```bash
cd ai_server
python -c "import ast; ast.parse(open('server.py').read()); print('syntax OK')"
```

Expected: `syntax OK`

**Step 3: uvicorn import 확인 (실제 서버 기동 없이)**

```bash
cd ai_server
python -c "from server import app; print('import OK')"
```

Expected: `import OK`

> **참고:** 이 명령은 `.env`에 OPENAI_API_KEY 등이 없으면 실패할 수 있다. 실패 시 `SyntaxError`나 `ImportError`가 아닌 환경변수 관련 오류이면 정상이다.

---

### Task 6: 전체 커밋

**Step 1: staging 확인**

```bash
git status
```

Expected:
```
Changes to be committed:
  renamed:    server.py -> ai_server/server.py
  deleted:    ai_server/main.py

Changes not staged for commit:
  modified:   README.md
  modified:   ai_server/server.py
```

**Step 2: 전체 변경사항 스테이징 및 커밋**

```bash
git add ai_server/server.py ai_server/main.py README.md
git commit -m "refactor: server.py를 ai_server/로 이동, sys.path 해킹 제거"
```

Expected: 커밋 성공

---

## 완료 기준

- [ ] `server.py`가 루트에 없고 `ai_server/server.py`로 존재
- [ ] `sys.path.insert` 줄이 `ai_server/server.py`에 없음
- [ ] `ai_server/main.py`가 삭제됨
- [ ] README.md의 pip install, uvicorn 명령, 구조 다이어그램이 업데이트됨
- [ ] `python -c "from server import app"` 이 `ai_server/` 내에서 실행 가능 (또는 환경변수 오류만 발생)
