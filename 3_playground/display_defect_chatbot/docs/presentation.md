# Display Defect Chatbot — 발표 자료

---

## 1. 프로젝트 개요

**디스플레이 패널 픽셀 불량 AI 분석 챗봇**

| 항목 | 내용 |
|---|---|
| 목적 | 불량 설명 입력 → RAG 기반 가설 생성 → 병렬 DB 분석 → 액션 플랜 제시 |
| 특징 | LangGraph Stateful Graph (세션 복원 가능), 병렬 서브에이전트 |
| 기술 | Vue 3 · Spring Boot · FastAPI · LangGraph · PostgreSQL + pgvector |

---

## 2. 전체 아키텍처

```mermaid
graph TD
    Browser["🖥️ Browser"]
    Frontend["Frontend<br/>Vue 3 + Vite<br/>:5174"]
    Backend["Backend<br/>Spring Boot<br/>:8080"]
    AIServer["AI Server<br/>FastAPI + LangGraph<br/>:8000"]
    PG[("PostgreSQL + pgvector<br/>:5432<br/>앱 DB + LangGraph 체크포인트")]

    Browser -- "/api/*" --> Frontend
    Frontend -- "proxy /api/*" --> Backend
    Backend -- "/internal/*" --> AIServer
    AIServer -- "SQL / pgvector" --> PG

    subgraph AIServer_내부["AI Server 내부"]
        RAG["RAG<br/>(pgvector 유사도 검색)"]
        Graph["LangGraph<br/>Stateful Graph"]
        Saver["AsyncPostgresSaver<br/>(체크포인트)"]
    end
```

---

## 3. 사용자 인터랙션 흐름

```mermaid
sequenceDiagram
    actor User as 사용자
    participant FE as Frontend
    participant BE as Backend
    participant AI as AI Server

    User->>FE: ① 불량 정보 입력<br/>(회사·제품ID·불량 설명)
    FE->>BE: POST /api/chat/agent<br/>action: start
    BE->>AI: POST /internal/agent
    AI-->>BE: hypotheses (가설 목록)
    BE-->>FE: 가설 목록 반환
    FE-->>User: ② 가설 목록 표시

    User->>FE: ③ 가설 선택 + 에이전트 ON/OFF
    FE->>BE: POST /api/chat/agent<br/>action: select_hypothesis
    BE->>AI: POST /internal/agent
    Note over AI: 병렬 서브에이전트 실행
    AI-->>BE: agentResults + longTermTaskId
    BE-->>FE: 분석 결과 반환
    FE-->>User: ④ 에이전트 분석 결과 표시

    opt 장기이력 활성화 시
        loop 폴링
            FE->>BE: GET /api/chat/bg-status/{taskId}
            BE-->>FE: status: pending/done
        end
        FE->>BE: POST /api/chat/agent<br/>action: resume_long_term
        BE->>AI: POST /internal/agent
    end

    AI-->>BE: finalActionPlan
    BE-->>FE: 최종 액션 플랜
    FE-->>User: ⑤ 액션 플랜 표시

    loop Q&A 무한 반복
        User->>FE: ⑥ 추가 질문
        FE->>BE: POST /api/chat/agent<br/>action: chat
        BE->>AI: POST /internal/agent
        AI-->>BE: reply
        BE-->>FE: AI 답변
        FE-->>User: 답변 표시
    end
```

---

## 4. LangGraph 그래프 노드 구조

```mermaid
flowchart TD
    START(["▶ START"])
    HN["hypothesis_node<br/>────────────────<br/>• RAG 유사도 검색<br/>• LLM 가설 생성<br/>• interrupt(hypotheses)"]

    subgraph FANOUT["병렬 팬아웃 (Send API)"]
        PH["process_history_node<br/>공정이력 조회·분석"]
        RH["return_history_node<br/>반송이력 조회·분석"]
        TR["test_result_node<br/>테스트결과 조회·분석"]
        LT["long_term_node<br/>장기이력 백그라운드<br/>(선택적)"]
    end

    ALT["await_long_term_node<br/>────────────────<br/>• 4개 결과 수집<br/>• interrupt(agentResults,<br/>  longTermTaskId)"]

    FSN["final_synthesis_node<br/>────────────────<br/>• 전체 결과 통합<br/>• LLM 액션 플랜 생성"]

    CN["chat_node<br/>────────────────<br/>• 분석 결과 기반 Q&A<br/>• interrupt(reply)<br/>• 자기 자신으로 루프"]

    END(["⏹ END"])

    START --> HN
    HN -- "route_to_agents<br/>(conditional edge)" --> FANOUT
    PH --> ALT
    RH --> ALT
    TR --> ALT
    LT --> ALT
    ALT --> FSN
    FSN --> CN
    CN -- "루프" --> CN
    CN --> END

    style HN fill:#dbeafe,stroke:#3b82f6
    style FANOUT fill:#fef9c3,stroke:#eab308
    style ALT fill:#dcfce7,stroke:#22c55e
    style FSN fill:#fce7f3,stroke:#ec4899
    style CN fill:#ede9fe,stroke:#8b5cf6
```

---

## 5. 핵심 메커니즘: interrupt / Command(resume)

```mermaid
sequenceDiagram
    participant HTTP as HTTP 요청
    participant Graph as LangGraph Graph
    participant PG as PostgreSQL (체크포인트)

    HTTP->>Graph: graph.ainvoke(initial_state)<br/>config: {thread_id: session_id}
    Graph->>Graph: 노드 실행...
    Graph->>PG: 현재 상태 전체 직렬화 저장
    Graph-->>HTTP: interrupt() → HTTP 응답 반환

    Note over HTTP,PG: ── 다음 HTTP 요청 ──

    HTTP->>Graph: graph.ainvoke(Command(resume=값))<br/>config: {thread_id: session_id}
    PG-->>Graph: 스냅샷 복원
    Graph->>Graph: interrupt() 이후 지점부터 재개
    Graph->>PG: 새 상태 저장
    Graph-->>HTTP: 다음 interrupt() → HTTP 응답 반환
```

> **핵심**: 각 HTTP 요청은 그래프를 처음부터 실행하지 않고 **마지막 interrupt 지점부터 재개**합니다.
> `thread_id = session_id`로 브라우저 탭마다 독립 세션이 유지됩니다.

---

## 6. State 생명주기

```mermaid
timeline
    title DefectAnalysisState 필드 업데이트 타임라인
    action\: start
        : company
        : defect_description
        : product_id
        : session_id
        : enabled_agents
    hypothesis_node 완료
        : hypotheses
        : selected_hypothesis
    병렬 에이전트 완료
        : process_history_result
        : return_history_result
        : test_result
        : long_term_task_id
    resume_long_term
        : long_term_result
    final_synthesis_node 완료
        : final_action_plan
    chat_node (누적)
        : messages[]
```

---

## 7. 병렬 서브에이전트 상세

```mermaid
graph LR
    Input["SubAgentInput<br/>────────────<br/>company<br/>defect_description<br/>product_id<br/>selected_hypothesis<br/>session_id"]

    subgraph Agents["병렬 실행 (Send API)"]
        A1["ProcessHistoryAgent<br/>─────────────<br/>SELECT * FROM process_history<br/>→ SQL 결과 분석<br/>→ AgentAnalysisResult"]
        A2["ReturnHistoryAgent<br/>─────────────<br/>SELECT * FROM return_history<br/>→ SQL 결과 분석<br/>→ AgentAnalysisResult"]
        A3["TestResultAgent<br/>─────────────<br/>SELECT * FROM test_results<br/>→ SQL 결과 분석<br/>→ AgentAnalysisResult"]
        A4["LongTermAgent<br/>─────────────<br/>백그라운드 실행<br/>→ task_id 반환<br/>(선택적 활성화)"]
    end

    Output["AgentAnalysisResult<br/>────────────<br/>suspect_rows: list<br/>analysis: str"]

    Input --> A1 & A2 & A3 & A4
    A1 & A2 & A3 --> Output
    A4 -- "비동기<br/>(longTermTaskId)" --> Output
```

---

## 8. 체크포인트 테이블 구조

```mermaid
erDiagram
    checkpoints {
        text thread_id PK
        int step PK
        timestamp created_at
    }
    checkpoint_blobs {
        text thread_id FK
        int step FK
        bytea blob "DefectAnalysisState 직렬화"
    }
    checkpoint_writes {
        text thread_id FK
        int step FK
        json writes "interrupt 직전 write 목록"
    }

    checkpoints ||--|{ checkpoint_blobs : "1:N"
    checkpoints ||--|{ checkpoint_writes : "1:N"
```

---

## 9. 기술 스택 요약

```mermaid
graph BT
    subgraph DB["데이터 레이어"]
        PG[("PostgreSQL 16<br/>+ pgvector")]
    end

    subgraph AI["AI 레이어 (FastAPI :8000)"]
        LG["LangGraph 1.x<br/>StateGraph + Send API"]
        LC["LangChain<br/>RAG · LLM Chain"]
        OAI["OpenAI<br/>gpt-4o-mini<br/>text-embedding-3-small"]
    end

    subgraph BE["비즈니스 레이어 (Spring Boot :8080)"]
        SB["Spring Boot<br/>Java 17"]
    end

    subgraph FE["프레젠테이션 레이어 (Vite :5174)"]
        VUE["Vue 3 + Vite"]
    end

    PG --> LG & LC
    LG & LC --> OAI
    AI --> BE
    BE --> FE
```

---

## 10. 주요 설계 포인트

| 포인트 | 설명 |
|---|---|
| **Stateful Graph** | `interrupt()` + `Command(resume=)` + `AsyncPostgresSaver`로 서버 재시작 후에도 세션 복원 |
| **병렬 팬아웃** | LangGraph `Send API`로 3~4개 서브에이전트를 동시에 실행, `await_long_term_node`에서 자동 fan-in |
| **장기이력 비동기** | 오래 걸리는 장기이력 조회는 백그라운드 태스크로 분리, 프론트는 폴링으로 상태 확인 |
| **config 주입** | `RunnableConfig`로 `VectorStoreManager`를 노드에 주입, DB 커넥션을 그래프 외부에서 관리 |
| **add_messages reducer** | Q&A 이력은 `add_messages` reducer로 자동 누적, 별도 설계 없이 무한 대화 루프 구현 |
| **단일 DB** | 앱 데이터(불량이력 등)와 LangGraph 체크포인트를 같은 PostgreSQL 인스턴스에서 관리 |
