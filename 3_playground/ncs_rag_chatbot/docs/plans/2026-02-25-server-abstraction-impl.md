# server.py 패키지 인터페이스 의존 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `server.py`의 버전 경로 직접 import를 패키지 레벨 re-export로 교체하여, 버전(`v1`)을 모르는 상태로 만든다.

**Architecture:** 각 패키지의 `__init__.py`가 이미 올바른 re-export를 제공하므로, `server.py`의 import 3줄만 수정한다. 기능 변경 없는 순수 리팩토링.

**Tech Stack:** Python 3.11, FastAPI

---

## 사전 확인

```bash
cd ai_server
pytest eval/tests/ tests/ -v
# Expected: 39 passed
```

---

## Task 1: server.py — 버전 경로 import → 패키지 import 교체

**Files:**
- Modify: `ai_server/server.py` (lines 34-38)

**Step 1: 현재 상태 확인**

```bash
grep -n "from agents\|from tools\|from clients" ai_server/server.py
```

Expected:
```
34: from agents.v1.rag_agent import ChatAgent
35: from agents.v1.sql_agent import SqlAgent
36: from agents.v1.supervisor import SupervisorAgent
37: from tools.rag_tool import ToolBuilder
38: from clients.spring.v1.employee import EmployeeClientV1
```

**Step 2: import 교체**

`ai_server/server.py` lines 34-38을 아래로 교체:

```python
# Before
from agents.v1.rag_agent import ChatAgent
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder
from clients.spring.v1.employee import EmployeeClientV1

# After
from agents import ChatAgent, SqlAgent, SupervisorAgent
from tools import ToolBuilder
from clients.spring import EmployeeClientV1
```

**Step 3: 테스트 실행 — PASS 확인**

```bash
cd ai_server && pytest eval/tests/ tests/ -v 2>&1 | tail -5
# Expected: 39 passed
```

**Step 4: server.py에 버전 경로가 남아있지 않은지 확인**

```bash
grep -n "\.v1\." ai_server/server.py
# Expected: (출력 없음)
```

**Step 5: 커밋**

```bash
git add ai_server/server.py
git commit -m "refactor(server): 버전 경로 직접 import → 패키지 인터페이스로 교체"
```
