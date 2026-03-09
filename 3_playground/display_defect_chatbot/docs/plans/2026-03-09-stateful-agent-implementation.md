# Stateful Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `/analyze` + `/investigate` 두 엔드포인트를 단일 `POST /internal/agent`로 통합하고, LangGraph `interrupt()`/`Command(resume=...)` + PostgresSaver 기반 stateful 그래프로 리팩토링한다.

**Architecture:** `hypothesis_node → (interrupt) → investigation_dispatch (Send API 병렬) → await_long_term_node (interrupt) → final_synthesis_node (interrupt) → chat_node (interrupt loop)`. PostgresSaver가 thread_id=session_id로 모든 상태를 DB에 영속화한다.

**Tech Stack:** LangGraph 1.x interrupt/Command, AsyncPostgresSaver (langgraph-checkpoint-postgres), FastAPI, Spring Boot, Vue 3

**Design Doc:** `docs/plans/2026-03-09-stateful-agent-refactoring-design.md`

---

## Task 1: requirements.txt + config.py + checkpointer.py

**Files:**
- Modify: `ai_server/requirements.txt`
- Modify: `ai_server/config.py`
- Create: `ai_server/infra/checkpointer.py`

### Step 1: requirements.txt에 패키지 추가

`ai_server/requirements.txt`의 `langgraph-checkpoint==4.0.0` 줄 아래에 추가:

```
langgraph-checkpoint-postgres==2.0.10
```

> langgraph-checkpoint-postgres는 psycopg3 기반. 이미 `psycopg==3.3.2`, `psycopg-binary==3.3.2`, `psycopg-pool==3.3.0`이 설치되어 있으므로 추가 psycopg 패키지 불필요.

### Step 2: config.py에 checkpoint URL 프로퍼티 추가

기존 `pg_sync_url`은 SQLAlchemy psycopg2 형식이므로, PostgresSaver용 psycopg3 형식 URL을 별도 추가.

`ai_server/config.py`의 `pg_sync_url` 프로퍼티 아래에 추가:

```python
@property
def pg_checkpoint_url(self) -> str:
    """AsyncPostgresSaver용 psycopg3 connection string (postgresql://...)"""
    return (
        f"postgresql://{self.postgres_user}:{self.postgres_password}"
        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )
```

### Step 3: checkpointer.py 생성

```python
# ai_server/infra/checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def create_checkpointer(pg_url: str) -> AsyncPostgresSaver:
    """AsyncPostgresSaver 생성 및 LangGraph 체크포인트 테이블 자동 초기화."""
    checkpointer = AsyncPostgresSaver.from_conn_string(pg_url)
    await checkpointer.setup()  # checkpoints, checkpoint_blobs, checkpoint_writes 테이블 자동 생성
    return checkpointer
```

### Step 4: 패키지 설치 확인

```bash
cd ai_server
pip install langgraph-checkpoint-postgres==2.0.10
```

Expected: Successfully installed langgraph-checkpoint-postgres

### Step 5: commit

```bash
git add ai_server/requirements.txt ai_server/config.py ai_server/infra/checkpointer.py
git commit -m "feat(ai): add AsyncPostgresSaver infrastructure"
```

---

## Task 2: state.py 리팩토링

**Files:**
- Modify: `ai_server/agents/state.py`

현재 state에서 `hypotheses`, `long_term_result`, `messages` 필드가 없음. 추가한다.

### Step 1: state.py 전체 교체

```python
# ai_server/agents/state.py
from typing import Annotated, Optional, TypedDict
from langchain_core.messages import BaseMessage, AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentOutputSchema(BaseModel):
    """with_structured_output용 Pydantic 스키마 (sub-agent 3종 공통)"""
    suspect_rows: list = Field(description="문제 원인으로 의심되는 row들 (원본 데이터 형식 그대로)")
    analysis: str = Field(description="에이전트 분석 결과 텍스트 2-3문장")


class SubAgentInput(TypedDict):
    """Send API로 서브에이전트에 전달되는 입력 전용 상태"""
    company: str
    defect_description: str
    product_id: str
    selected_hypothesis: str
    session_id: str


class AgentAnalysisResult(TypedDict):
    """각 분석 에이전트의 결과: 의심 row 목록 + 분석 텍스트"""
    suspect_rows: list
    analysis: str


class DefectAnalysisState(TypedDict):
    """전체 그래프 상태"""

    # ── 입력 (불변) ──────────────────────────
    company: str
    defect_description: str
    product_id: str
    session_id: str
    enabled_agents: list[str]

    # ── 가설 단계 ────────────────────────────
    hypotheses: list[str]
    selected_hypothesis: str

    # ── 에이전트 결과 (reducer: 최신값으로 교체) ──
    process_history_result: Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    return_history_result:  Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    test_result:            Annotated[Optional[AgentAnalysisResult], lambda _, u: u]
    long_term_task_id:      Annotated[Optional[str], lambda _, u: u]
    long_term_result:       Annotated[Optional[str], lambda _, u: u]

    # ── 최종 출력 ────────────────────────────
    final_action_plan: str

    # ── Q&A 대화 이력 (add_messages reducer로 누적) ──
    messages: Annotated[list[AnyMessage], add_messages]
```

### Step 2: commit

```bash
git add ai_server/agents/state.py
git commit -m "feat(ai): extend DefectAnalysisState with hypotheses, long_term_result, messages"
```

---

## Task 3: prompts.py에 FINAL_SYNTHESIS + CHAT 프롬프트 추가

**Files:**
- Modify: `ai_server/agents/prompts.py`

### Step 1: 파일 끝에 두 프롬프트 추가

```python
FINAL_SYNTHESIS_SYSTEM_PROMPT = """당신은 삼성 디스플레이 품질관리 전문가입니다.
공정이력, 반송이력, 테스트결과, 장기이력 데이터를 모두 종합하여 구체적인 조치 방안을 제시하세요.

응답 구조:
## 원인 분석 요약
(선택된 가설 + 수집 데이터 기반 분석)

## 즉시 조치 사항
1. ...
2. ...

## 재발 방지 대책
1. ...
2. ...

## 추가 확인 필요 사항
- ..."""


CHAT_SYSTEM_PROMPT = """당신은 삼성 디스플레이 품질관리 전문가입니다.
이전 분석 결과를 바탕으로 사용자의 추가 질문에 답변하세요.
답변은 명확하고 실용적으로 작성하세요."""
```

### Step 2: commit

```bash
git add ai_server/agents/prompts.py
git commit -m "feat(ai): add FINAL_SYNTHESIS and CHAT system prompts"
```

---

## Task 4: graph.py 전면 재작성

**Files:**
- Rewrite: `ai_server/agents/graph.py`
- Delete logic: `ai_server/agents/main_agent.py` (hypothesis_node로 흡수됨, 파일은 유지)
- Modify: `ai_server/agents/synthesis_node.py` → `final_synthesis_node`로 업데이트

### Step 1: synthesis_node.py 업데이트

장기이력 데이터를 포함하고, 프롬프트를 `FINAL_SYNTHESIS_SYSTEM_PROMPT`로 교체.

`ai_server/agents/synthesis_node.py` 전체 교체:

```python
# ai_server/agents/synthesis_node.py
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ai_server.agents.state import DefectAnalysisState
from ai_server.agents.prompts import FINAL_SYNTHESIS_SYSTEM_PROMPT
from ai_server.config import get_settings

settings = get_settings()
_llm = ChatOpenAI(model=settings.model_name, temperature=0.2)


def _fmt(result: dict | None) -> str:
    if not result:
        return "데이터 없음"
    return f"분석: {result.get('analysis', '')}\n의심 데이터: {json.dumps(result.get('suspect_rows', []), ensure_ascii=False, default=str, indent=2)}"


async def final_synthesis_node(state: DefectAnalysisState) -> dict:
    """3개 에이전트 + 장기이력 결과를 모두 포함한 최종 조치안 생성"""
    content = f"""
[선택된 가설]: {state["selected_hypothesis"]}
[불량 증상]: {state["defect_description"]}
[회사]: {state["company"]}

[공정이력 에이전트 분석]
{_fmt(state.get("process_history_result"))}

[반송이력 에이전트 분석]
{_fmt(state.get("return_history_result"))}

[테스트결과 에이전트 분석]
{_fmt(state.get("test_result"))}

[장기이력 분석]
{state.get("long_term_result") or "데이터 없음"}
"""
    messages = [
        SystemMessage(content=FINAL_SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]
    response = await _llm.ainvoke(messages)
    return {"final_action_plan": response.content}
```

### Step 2: graph.py 전면 재작성

```python
# ai_server/agents/graph.py
"""
Stateful LangGraph — interrupt()/Command(resume=...) + AsyncPostgresSaver

흐름:
  START → hypothesis_node (interrupt: hypotheses 반환)
        → investigation_dispatch (Send API 병렬)
        → await_long_term_node (interrupt: agent_results + task_id 반환)
        → final_synthesis_node
        → chat_node (interrupt loop: Q&A)
"""
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, interrupt, Command

from ai_server.agents.prompts import (
    HYPOTHESIS_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
)
from ai_server.agents.state import DefectAnalysisState, SubAgentInput
from ai_server.agents.sub.process_history import process_history_node
from ai_server.agents.sub.return_history import return_history_node
from ai_server.agents.sub.test_result import test_result_node
from ai_server.agents.sub.long_term import long_term_node
from ai_server.agents.synthesis_node import final_synthesis_node
from ai_server.config import get_settings
from ai_server.infra.graph_logger import apply_middleware, build_node_middleware
from ai_server.infra.vector_store import VectorStoreManager

settings = get_settings()
_llm = ChatOpenAI(model=settings.model_name, temperature=0.3)
_chat_llm = ChatOpenAI(model=settings.model_name, temperature=0.5)

_INPUT_KEYS = tuple(SubAgentInput.__annotations__)

_NODE_MAP = {
    "process_history": "process_history_node",
    "return_history":  "return_history_node",
    "test_result":     "test_result_node",
    "long_term":       "long_term_node",
}
ALL_AGENTS: list[str] = list(_NODE_MAP.keys())


# ── 노드 정의 ──────────────────────────────────────────────────────────────

async def hypothesis_node(state: DefectAnalysisState, config: RunnableConfig) -> dict:
    """RAG 검색 → 가설 생성 → interrupt(가설 목록) → 선택된 가설 수신"""
    vsm: VectorStoreManager = config["configurable"]["vsm"]
    docs = await vsm.similarity_search(state["defect_description"], k=4)
    context = "\n\n".join([d.page_content for d in docs]) if docs else "관련 사례 없음"

    messages = [
        SystemMessage(content=HYPOTHESIS_SYSTEM_PROMPT),
        HumanMessage(
            content=f"[보고 회사]: {state['company']}\n[불량 증상]: {state['defect_description']}\n\n[과거 사례 문서]\n{context}"
        ),
    ]
    response = await _llm.ainvoke(messages)
    text = response.content.strip()

    hypotheses = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("가설") and ":" in line:
            hypotheses.append(line)
    if not hypotheses:
        hypotheses = [text]

    # interrupt: 클라이언트에 가설 목록 반환, 선택된 가설 수신
    selected_hypothesis: str = interrupt({"hypotheses": hypotheses})

    return {
        "hypotheses": hypotheses,
        "selected_hypothesis": selected_hypothesis,
    }


def route_to_agents(state: DefectAnalysisState) -> list[Send]:
    """Send API: enabled_agents에 포함된 에이전트만 병렬 팬아웃"""
    sub_state = {k: state[k] for k in _INPUT_KEYS}
    enabled = state.get("enabled_agents") or ALL_AGENTS
    return [Send(_NODE_MAP[key], sub_state) for key in enabled if key in _NODE_MAP]


async def await_long_term_node(state: DefectAnalysisState) -> dict:
    """병렬 에이전트 완료 후 interrupt: agent_results + task_id 반환, 장기이력 결과 수신"""
    agent_results = {
        "process_history": state.get("process_history_result"),
        "return_history":  state.get("return_history_result"),
        "test_result":     state.get("test_result"),
    }
    long_term_result: str = interrupt({
        "agent_results": agent_results,
        "long_term_task_id": state.get("long_term_task_id"),
    })
    return {"long_term_result": long_term_result}


async def chat_node(state: DefectAnalysisState) -> dict:
    """Q&A 루프: interrupt로 user_message 수신 → LLM 응답 → 메시지 누적"""
    user_message: str = interrupt({"final_action_plan": state.get("final_action_plan", "")})

    context = f"""[최종 조치안]
{state.get('final_action_plan', '')}

[불량 증상]: {state['defect_description']}
[선택된 가설]: {state.get('selected_hypothesis', '')}"""

    messages = [
        SystemMessage(content=CHAT_SYSTEM_PROMPT + "\n\n" + context),
        *state.get("messages", []),
        HumanMessage(content=user_message),
    ]
    response = await _chat_llm.ainvoke(messages)

    return {
        "messages": [
            HumanMessage(content=user_message),
            AIMessage(content=response.content),
        ]
    }


# ── 그래프 빌드 ────────────────────────────────────────────────────────────

def build_investigation_graph(checkpointer):
    builder = StateGraph(DefectAnalysisState)
    mw = build_node_middleware(settings)

    builder.add_node("hypothesis_node",       apply_middleware(hypothesis_node,       "hypothesis_node",       mw))
    builder.add_node("process_history_node",  apply_middleware(process_history_node,  "process_history_node",  mw))
    builder.add_node("return_history_node",   apply_middleware(return_history_node,   "return_history_node",   mw))
    builder.add_node("test_result_node",      apply_middleware(test_result_node,      "test_result_node",      mw))
    builder.add_node("long_term_node",        apply_middleware(long_term_node,        "long_term_node",        mw))
    builder.add_node("await_long_term_node",  apply_middleware(await_long_term_node,  "await_long_term_node",  mw))
    builder.add_node("final_synthesis_node",  apply_middleware(final_synthesis_node,  "final_synthesis_node",  mw))
    builder.add_node("chat_node",             apply_middleware(chat_node,             "chat_node",             mw))

    # START → hypothesis → Send API 병렬
    builder.add_edge(START, "hypothesis_node")
    builder.add_conditional_edges("hypothesis_node", route_to_agents)

    # 병렬 에이전트 → await_long_term (LangGraph: 모든 선행 노드 완료 후 실행)
    builder.add_edge("process_history_node", "await_long_term_node")
    builder.add_edge("return_history_node",  "await_long_term_node")
    builder.add_edge("test_result_node",     "await_long_term_node")
    builder.add_edge("long_term_node",       "await_long_term_node")

    # await_long_term → synthesis → chat (loop)
    builder.add_edge("await_long_term_node", "final_synthesis_node")
    builder.add_edge("final_synthesis_node", "chat_node")
    builder.add_edge("chat_node", "chat_node")  # Q&A 루프

    return builder.compile(checkpointer=checkpointer)
```

### Step 3: main_agent.py 비활성화

`ai_server/agents/main_agent.py` 파일 상단에 deprecation 주석 추가 (삭제하지 않음):

```python
# DEPRECATED: hypothesis_node(graph.py)로 흡수됨. 이 파일은 더 이상 사용되지 않습니다.
```

### Step 4: commit

```bash
git add ai_server/agents/graph.py ai_server/agents/synthesis_node.py ai_server/agents/main_agent.py
git commit -m "feat(ai): rewrite graph with interrupt-based stateful flow"
```

---

## Task 5: server.py 전면 재작성

**Files:**
- Rewrite: `ai_server/server.py`

### Step 1: server.py 전체 교체

```python
# ai_server/server.py
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from langchain_openai import OpenAIEmbeddings
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
import os
import tempfile

from ai_server.agents.graph import build_investigation_graph, ALL_AGENTS, DefectAnalysisState
from ai_server.config import get_settings
from ai_server.infra.checkpointer import create_checkpointer
from ai_server.infra.ingest import ingest_document
from ai_server.infra.vector_store import VectorStoreManager
from ai_server.tools.sql_tools import get_bg_task

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedding = OpenAIEmbeddings(model=settings.embedding_model)
    app.state.vsm = await VectorStoreManager.create(settings.pg_async_url, embedding)
    app.state.checkpointer = await create_checkpointer(settings.pg_checkpoint_url)
    app.state.graph = build_investigation_graph(app.state.checkpointer)
    yield


app = FastAPI(title="Defect AI Server", lifespan=lifespan)


# ── Request / Response Models ──────────────────────────────────────────────

class AgentRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    session_id: str
    action: str  # "start" | "select_hypothesis" | "resume_long_term" | "chat"
    company: str = ""
    defect_description: str = ""
    product_id: str = ""
    enabled_agents: list[str] = list(ALL_AGENTS)
    # action별 선택 필드
    selected_hypothesis: Optional[str] = None
    long_term_result: Optional[str] = None
    user_message: Optional[str] = None


class AgentResponse(BaseModel):
    action: str
    # start
    hypotheses: Optional[list[str]] = None
    # select_hypothesis
    agent_results: Optional[dict] = None
    long_term_task_id: Optional[str] = None
    # resume_long_term
    final_action_plan: Optional[str] = None
    # chat
    reply: Optional[str] = None


class BgStatusResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    task_id: str
    status: str
    result_text: Optional[str] = None


# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _parse_interrupt(result: dict) -> dict:
    """graph.ainvoke() 반환값에서 interrupt value 추출"""
    interrupts = result.get("__interrupt__", [])
    if interrupts:
        return interrupts[0].value
    return {}


def _build_response(interrupt_value: dict, action: str) -> AgentResponse:
    if "hypotheses" in interrupt_value:
        return AgentResponse(action="start", hypotheses=interrupt_value["hypotheses"])
    if "agent_results" in interrupt_value:
        return AgentResponse(
            action="select_hypothesis",
            agent_results=interrupt_value["agent_results"],
            long_term_task_id=interrupt_value.get("long_term_task_id"),
        )
    if "final_action_plan" in interrupt_value:
        return AgentResponse(action="resume_long_term", final_action_plan=interrupt_value["final_action_plan"])
    # chat_node interrupt: final_action_plan이 있으면 첫 chat interrupt
    # resume 후 chat 응답은 messages에서 추출
    return AgentResponse(action=action)


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/internal/agent", response_model=AgentResponse)
async def agent_endpoint(req: AgentRequest, request: Request):
    """단일 엔드포인트: action에 따라 그래프 start 또는 resume"""
    graph = request.app.state.graph
    vsm = request.app.state.vsm

    config = {
        "configurable": {
            "thread_id": req.session_id,
            "vsm": vsm,
        }
    }

    if req.action == "start":
        initial_state: DefectAnalysisState = {
            "company": req.company,
            "defect_description": req.defect_description,
            "product_id": req.product_id,
            "session_id": req.session_id,
            "enabled_agents": req.enabled_agents,
            "hypotheses": [],
            "selected_hypothesis": "",
            "process_history_result": None,
            "return_history_result": None,
            "test_result": None,
            "long_term_task_id": None,
            "long_term_result": None,
            "final_action_plan": "",
            "messages": [],
        }
        result = await graph.ainvoke(initial_state, config=config)

    else:
        resume_map = {
            "select_hypothesis": req.selected_hypothesis,
            "resume_long_term":  req.long_term_result,
            "chat":              req.user_message,
        }
        resume_value = resume_map.get(req.action)
        if resume_value is None:
            raise HTTPException(status_code=400, detail=f"Unknown action or missing payload: {req.action}")
        result = await graph.ainvoke(Command(resume=resume_value), config=config)

    interrupt_value = _parse_interrupt(result)

    # chat resume 후: interrupt_value는 다음 chat interrupt (final_action_plan 포함)
    # 하지만 실제 chat 응답은 messages 마지막 AIMessage에 있음
    if req.action == "chat" and "messages" in result:
        msgs = result["messages"]
        if msgs:
            last_ai = next((m for m in reversed(msgs) if hasattr(m, "type") and m.type == "ai"), None)
            if last_ai:
                return AgentResponse(action="chat", reply=last_ai.content)

    return _build_response(interrupt_value, req.action)


@app.get("/internal/bg-status/{task_id}", response_model=BgStatusResponse, response_model_by_alias=True)
async def get_bg_status(task_id: str):
    """백그라운드 장기이력 분석 완료 상태 조회"""
    row = await get_bg_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return BgStatusResponse(**row)


@app.post("/internal/ingest")
async def ingest(doc_id: str, request: Request, file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        count = await ingest_document(doc_id, tmp_path, request.app.state.vsm)
        return {"doc_id": doc_id, "chunks": count}
    finally:
        os.unlink(tmp_path)


@app.delete("/internal/delete/{doc_id}")
async def delete_document(doc_id: str, request: Request):
    deleted = await request.app.state.vsm.delete_by_doc_id(doc_id)
    return {"doc_id": doc_id, "deleted_chunks": deleted}


@app.get("/internal/health")
async def health():
    return {"status": "ok"}
```

### Step 2: 서버 기동 확인

```bash
cd ai_server
uvicorn ai_server.server:app --reload --port 8000
```

Expected: `Application startup complete.` (DB 연결 성공, 체크포인트 테이블 생성)

### Step 3: health check

```bash
curl http://localhost:8000/internal/health
```

Expected: `{"status":"ok"}`

### Step 4: commit

```bash
git add ai_server/server.py
git commit -m "feat(ai): rewrite server with single /agent endpoint and PostgresSaver"
```

---

## Task 6: Backend Spring 업데이트

**Files:**
- Create: `backend/src/main/java/com/sdi/chatbot/dto/AgentRequest.java`
- Create: `backend/src/main/java/com/sdi/chatbot/dto/AgentResponse.java`
- Modify: `backend/src/main/java/com/sdi/chatbot/controller/ChatController.java`
- Modify: `backend/src/main/java/com/sdi/chatbot/service/ChatService.java`

### Step 1: AgentRequest.java 생성

```java
// backend/src/main/java/com/sdi/chatbot/dto/AgentRequest.java
package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;

@Data
public class AgentRequest {
    private String sessionId;
    private String action;           // "start" | "select_hypothesis" | "resume_long_term" | "chat"
    private String company;
    private String defectDescription;
    private String productId;
    private List<String> enabledAgents;
    // action별 선택 필드
    private String selectedHypothesis;
    private String longTermResult;
    private String userMessage;
}
```

### Step 2: AgentResponse.java 생성

```java
// backend/src/main/java/com/sdi/chatbot/dto/AgentResponse.java
package com.sdi.chatbot.dto;

import lombok.Data;
import java.util.List;
import java.util.Map;

@Data
public class AgentResponse {
    private String action;
    // start
    private List<String> hypotheses;
    // select_hypothesis
    private Map<String, Object> agentResults;
    private String longTermTaskId;
    // resume_long_term
    private String finalActionPlan;
    // chat
    private String reply;
}
```

### Step 3: ChatController.java 교체

기존 `analyze`, `investigate`, `agent/{agentName}` 제거. `agent` + `bg-status` 만 남김:

```java
package com.sdi.chatbot.controller;

import com.sdi.chatbot.dto.AgentRequest;
import com.sdi.chatbot.dto.AgentResponse;
import com.sdi.chatbot.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("/agent")
    public ResponseEntity<AgentResponse> agent(@RequestBody AgentRequest request) {
        return ResponseEntity.ok(chatService.agent(request));
    }

    @GetMapping("/bg-status/{taskId}")
    public ResponseEntity<Object> getBgStatus(@PathVariable String taskId) {
        return ResponseEntity.ok(chatService.getBgStatus(taskId));
    }
}
```

### Step 4: ChatService.java 교체

```java
package com.sdi.chatbot.service;

import com.sdi.chatbot.dto.AgentRequest;
import com.sdi.chatbot.dto.AgentResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final RestClient aiRestClient;

    public AgentResponse agent(AgentRequest request) {
        return aiRestClient.post()
                .uri("/internal/agent")
                .body(request)
                .retrieve()
                .body(AgentResponse.class);
    }

    public Object getBgStatus(String taskId) {
        return aiRestClient.get()
                .uri("/internal/bg-status/" + taskId)
                .retrieve()
                .body(Object.class);
    }
}
```

### Step 5: commit

```bash
git add backend/src/main/java/com/sdi/chatbot/dto/AgentRequest.java
git add backend/src/main/java/com/sdi/chatbot/dto/AgentResponse.java
git add backend/src/main/java/com/sdi/chatbot/controller/ChatController.java
git add backend/src/main/java/com/sdi/chatbot/service/ChatService.java
git commit -m "feat(backend): unify to single /agent endpoint"
```

---

## Task 7: Frontend 업데이트

**Files:**
- Modify: `frontend/src/api/defectApi.js`
- Modify: `frontend/src/composables/useDefectChat.js`

### Step 1: defectApi.js 교체

```javascript
// frontend/src/api/defectApi.js
const BASE = '/api'

export async function callAgent(payload) {
  const res = await fetch(`${BASE}/chat/agent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function getBgStatus(taskId) {
  const res = await fetch(`${BASE}/chat/bg-status/${taskId}`)
  return res.json()
}

// 문서 관리 (유지)
export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/documents`, { method: 'POST', body: form })
  return res.json()
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE}/documents`)
  return res.json()
}

export async function deleteDocument(docId) {
  await fetch(`${BASE}/documents/${docId}`, { method: 'DELETE' })
}
```

### Step 2: useDefectChat.js의 analyze/investigate/runAllEnabled를 callAgent 기반으로 교체

`useDefectChat.js`에서 아래 함수들을 교체:

**기존 `analyze()` 제거 → `startAnalysis()` 추가:**

```javascript
async function startAnalysis() {
  loading.value = true
  error.value = null
  try {
    const data = await callAgent({
      sessionId: sessionId.value,
      action: 'start',
      company: form.company,
      defectDescription: form.defectDescription,
      productId: form.productId,
      enabledAgents: AGENT_CONFIG.map(a => a.key),
    })
    hypotheses.value = data.hypotheses || []
    step.value = 'hypotheses'
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
```

**기존 `selectHypothesis()` 교체:**

```javascript
async function selectHypothesis(hypothesis) {
  selectedHypothesis.value = hypothesis
  step.value = 'result'
  loading.value = true
  chatMessages.value = []

  const enabledKeys = AGENT_CONFIG.map(a => a.key).filter(k => enabledAgents[k])
  enabledKeys.forEach(k => {
    agentLoading[k] = true
    chatMessages.value.push({ id: uuidv4(), agentKey: k, status: 'loading', result: null })
  })

  try {
    const data = await callAgent({
      sessionId: sessionId.value,
      action: 'select_hypothesis',
      selectedHypothesis: hypothesis,
    })

    const results = data.agentResults || {}
    for (const [key, val] of Object.entries(results)) {
      if (val) {
        const r = { suspectRows: val.suspect_rows || [], analysis: val.analysis || '' }
        agentResults[key] = r
        _updateMessage(key, 'done', r)
      }
    }
    if (data.longTermTaskId) pollBgStatus(data.longTermTaskId)
  } catch (e) {
    error.value = e.message
    enabledKeys.forEach(k => _updateMessage(k, 'error', null))
  } finally {
    enabledKeys.forEach(k => { agentLoading[k] = false })
    loading.value = false
    saveCurrentSession()
  }
}
```

**pollBgStatus 완료 시 resume_long_term 호출:**

```javascript
function pollBgStatus(taskId) {
  pollTimer.value = setInterval(async () => {
    try {
      const data = await getBgStatus(taskId)
      longTermStatus.value = data.status
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        clearInterval(pollTimer.value); pollTimer.value = null
        longTermResult.value = data.resultText

        if (data.status === 'COMPLETED') {
          // 그래프 resume: 장기이력 결과 전달 → final synthesis
          const response = await callAgent({
            sessionId: sessionId.value,
            action: 'resume_long_term',
            longTermResult: data.resultText || '',
          })
          const r = { suspectRows: [], analysis: data.resultText || '' }
          agentResults['long_term'] = r
          _updateMessage('long_term', 'done', r)
          finalActionPlan.value = response.finalActionPlan || ''
        } else {
          _updateMessage('long_term', 'error', null)
        }
        saveCurrentSession()
      }
    } catch (e) {
      clearInterval(pollTimer.value); pollTimer.value = null
    }
  }, 3000)
}
```

**sendUserMessage를 chat action으로 교체:**

```javascript
async function sendUserMessage() {
  const text = userInput.value.trim()
  if (!text) return
  userInput.value = ''
  chatMessages.value.push({ id: uuidv4(), agentKey: 'user', status: 'user', userText: text })

  try {
    const data = await callAgent({
      sessionId: sessionId.value,
      action: 'chat',
      userMessage: text,
    })
    if (data.reply) {
      chatMessages.value.push({ id: uuidv4(), agentKey: 'assistant', status: 'done', result: { analysis: data.reply, suspectRows: [] } })
    }
  } catch (e) {
    error.value = e.message
  }
}
```

**return 블록에서 `analyze` → `startAnalysis`로 변경:**

```javascript
return {
  ...,
  startAnalysis,   // analyze 대신
  selectHypothesis,
  sendUserMessage,
  ...
}
```

### Step 3: App.vue에서 `analyze` 호출을 `startAnalysis`로 변경

`frontend/src/App.vue`에서 `analyze(` → `startAnalysis(` 검색 후 교체.

### Step 4: commit

```bash
git add frontend/src/api/defectApi.js frontend/src/composables/useDefectChat.js frontend/src/App.vue
git commit -m "feat(frontend): migrate to single callAgent API with interrupt-based flow"
```

---

## Task 8: E2E 동작 확인

### Step 1: AI Server 재기동 + health check

```bash
curl http://localhost:8000/internal/health
```

### Step 2: start action curl 테스트

```bash
curl -X POST http://localhost:8000/internal/agent \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "action": "start",
    "company": "SDC",
    "defectDescription": "화면 좌측 상단 Dead Pixel",
    "productId": "LOT-A001",
    "enabledAgents": ["process_history", "return_history", "test_result", "long_term"]
  }'
```

Expected: `{"action":"start","hypotheses":["가설1:...","가설2:..."]}`

### Step 3: select_hypothesis curl 테스트

```bash
curl -X POST http://localhost:8000/internal/agent \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "action": "select_hypothesis",
    "selectedHypothesis": "가설1: TFT 공정 이상"
  }'
```

Expected: `{"action":"select_hypothesis","agentResults":{...},"longTermTaskId":"uuid"}`

### Step 4: chat curl 테스트 (resume_long_term 이후)

```bash
curl -X POST http://localhost:8000/internal/agent \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-session-001",
    "action": "chat",
    "userMessage": "이 가설 외에 다른 원인은 없을까요?"
  }'
```

Expected: `{"action":"chat","reply":"..."}`

### Step 5: PostgreSQL에 체크포인트 저장 확인

```bash
docker exec -it <postgres-container> psql -U postgres -d defect_db \
  -c "SELECT thread_id, checkpoint_id, created_at FROM checkpoints LIMIT 5;"
```

Expected: test-session-001 thread가 조회됨
