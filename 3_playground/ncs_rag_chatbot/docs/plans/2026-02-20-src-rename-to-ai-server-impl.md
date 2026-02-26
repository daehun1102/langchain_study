# src → ai_server 리네임 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `src/` 디렉토리를 `ai_server/`로 git mv 하고 연관된 경로 참조 3곳을 수정한다.

**Architecture:** git mv로 히스토리를 보존하며 디렉토리를 이동한 뒤, server.py sys.path / init_prompts.py 주석 / README.md 구조 표기를 순서대로 수정한다.

**Tech Stack:** git, Python, Markdown

---

### Task 1: git mv — src/ → ai_server/

**Files:**
- Rename: `src/` → `ai_server/`

**Step 1: git mv 실행**

```bash
git mv src ai_server
```

**Step 2: 결과 확인**

```bash
git status
```

Expected: `renamed: src/agent.py -> ai_server/agent.py` 등 11개 파일 renamed 표시

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: src → ai_server 디렉토리 리네임 (git mv)"
```

---

### Task 2: server.py — sys.path 수정

**Files:**
- Modify: `server.py:22`

**Step 1: 변경 전 확인**

`server.py` 22번째 줄:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
```

**Step 2: 수정**

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ai_server"))
```

**Step 3: Python 구문 검증**

```bash
python -c "import ast, pathlib; ast.parse(pathlib.Path('server.py').read_text(encoding='utf-8')); print('OK')"
```

Expected: `OK`

**Step 4: Commit**

```bash
git add server.py
git commit -m "fix: server.py sys.path src → ai_server"
```

---

### Task 3: ai_server/init_prompts.py — 주석 수정

**Files:**
- Modify: `ai_server/init_prompts.py:4`

**Step 1: 변경 전 확인**

`ai_server/init_prompts.py` 4번째 줄:
```
실행: python src/init_prompts.py
```

**Step 2: 수정**

```
실행: python ai_server/init_prompts.py
```

**Step 3: Commit**

```bash
git add ai_server/init_prompts.py
git commit -m "docs: init_prompts.py 실행 경로 주석 수정"
```

---

### Task 4: README.md — 디렉토리 구조 및 명령어 수정

**Files:**
- Modify: `README.md:115` (ingest 명령어)
- Modify: `README.md:241` (디렉토리 구조 표기)

**Step 1: 115번째 줄 수정**

변경 전:
```bash
python src/ingest.py init
```

변경 후:
```bash
python ai_server/ingest.py init
```

**Step 2: 241번째 줄 수정**

변경 전:
```
├── src/                            # Python AI 서버
```

변경 후:
```
├── ai_server/                      # Python AI 서버
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README 디렉토리 구조 ai_server 반영"
```
