# Human-in-the-loop (HITL) 정리

## 1. 개요
- **Human-in-the-Loop(HITL) 미들웨어**는 에이전트의 **툴 호출(tool call)** 에 사람의 검토(oversight)를 추가한다.
- 모델이 “검토가 필요할 수 있는 액션”을 제안하면(예: 파일 쓰기, SQL 실행 등), 미들웨어가 실행을 **일시 중단(pause)** 하고 사람의 결정을 기다린다.
- 중단은 정책(`interrupt_on`)에 따라 발생하며, 중단 시 **interrupt** 를 발생시켜 실행을 멈춘다.
- 중단된 동안 그래프 상태는 LangGraph의 **persistence(영속/저장) 레이어**를 통해 저장되어, 안전하게 **나중에 재개(resume)** 할 수 있다.
- 사람의 결정은 다음 중 하나로 처리된다:
  - 그대로 승인(`approve`)
  - 실행 전에 수정(`edit`)
  - 거절 + 피드백(`reject`)

<br>

## 2. Interrupt 결정 타입(Decision Types)
HITL 미들웨어는 interrupt에 대해 사람이 응답할 수 있는 **3가지 결정 타입**을 제공한다.

| Decision Type | 설명 | 예시 |
|---|---|---|
| ✅ `approve` | 액션을 **그대로 승인**하고 변경 없이 실행 | 작성된 이메일을 그대로 발송 |
| ✏️ `edit` | 실행 전에 **툴 호출 인자(args)를 수정**한 뒤 실행 | 이메일 수신자를 바꿔서 발송 |
| ❌ `reject` | 액션을 **거절**하고 이유/피드백을 대화에 추가 | 이메일 초안을 거절하고 수정 방향 제시 |

### 2.1 결정 타입 관련 규칙
- 각 툴에서 가능한 결정 타입은 `interrupt_on` 정책에 따라 달라진다.
- 동시에 여러 툴 호출이 중단되면, **각 액션마다 개별 결정**이 필요하다.
- 결정은 interrupt에 포함된 액션 요청 순서대로 제공해야 한다.
- `edit`는 **보수적으로(최소 변경)** 하는 것이 권장된다. 큰 변경은 모델이 접근 방식을 다시 평가하면서 툴을 여러 번 실행하거나 예상치 못한 행동을 유발할 수 있다.

<br>

## 3. Interrupt 설정(Configuring Interrupts)

### 3.1 HITL 미들웨어 추가 방법
에이전트 생성 시 `middleware` 리스트에 HITL 미들웨어를 추가한다.

- `interrupt_on`: 어떤 툴 호출을 어떤 방식으로 중단할지 정의하는 매핑
- `description_prefix`: interrupt 메시지의 설명 앞부분(prefix)

### 3.2 `interrupt_on` 값의 의미
`interrupt_on`의 값은 다음 형태 중 하나다.

- `True`  
  - 기본 설정으로 interrupt
  - 보통 `approve/edit/reject` 모두 가능(기본 정책)
- `False`  
  - interrupt 없이 자동 진행(승인 불필요)
- `InterruptOnConfig` 객체(dict)  
  - 허용 결정 타입 제한, 설명 커스터마이징 등 상세 설정 가능

<br>

## 4. 예제 코드 (설정)

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-4.1",
    tools=[write_file_tool, execute_sql_tool, read_data_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # 기본 설정으로 interrupt (일반적으로 approve/edit/reject 가능)
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # edit 금지
                "read_data": False,  # 안전한 작업: 승인 없이 자동 진행
            },
            description_prefix="Tool execution pending approval",
        ),
    ],
    # HITL은 interrupt 중단/재개를 위해 checkpointer가 필수
    # 프로덕션에서는 영속 checkpointer 권장(예: AsyncPostgresSaver)
    checkpointer=InMemorySaver(),
)
```

<br>

## 5. 체크포인터(Checkpointer) 필수 사항
- HITL은 실행이 중간에 중단되므로, 중단된 실행을 나중에 이어서 처리하려면 **그래프 상태 저장**이 필요하다.
- 따라서 HITL 사용 시 **checkpointer 설정은 필수**다.

권장:
- 테스트/프로토타입: `InMemorySaver`
- 프로덕션: 영속 저장소 기반 checkpointer (예: `AsyncPostgresSaver`)

<br>

## 6. Interrupt 응답(재개) 방법 (Responding to Interrupts)

### 6.1 기본 흐름
1. `agent.invoke(...)` 실행
2. 정책에 의해 interrupt 발생 시 결과에 `__interrupt__` 필드 포함
3. 사람이 `approve/edit/reject` 결정을 내려 `Command(resume=...)`로 재개

### 6.2 thread_id (중요)
- interrupt는 “중단된 실행”을 “같은 대화 스레드”에서 이어서 재개해야 한다.
- 따라서 invoke 시 `config`에 **thread_id**를 포함해야 한다.

<br>

## 7. 예제 코드 (interrupt 발생 후 승인/수정/거절)

### 7.1 interrupt까지 실행
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config
)

# interrupt가 발생하면 result에 '__interrupt__'가 포함됨
print(result["__interrupt__"])
```

`__interrupt__`에는 보통 다음 정보가 들어간다:
- `action_requests`: 검토가 필요한 액션 목록(툴 이름, 인자, 설명)
- `review_configs`: 각 액션별 허용 결정 타입 등 정책 정보

<br>

### 7.2 ✅ approve (그대로 승인)
```python
agent.invoke(
    Command(
        resume={"decisions": [{"type": "approve"}]}
    ),
    config=config
)
```

<br>

### 7.3 ✏️ edit (수정 후 실행)
- `edit`는 변경된 툴 호출을 `edited_action`에 제공한다.
- `edited_action`에는 `name`(툴 이름)과 `args`(인자)가 들어간다.

```python
agent.invoke(
    Command(
        resume={
            "decisions": [
                {
                    "type": "edit",
                    "edited_action": {
                        "name": "tool_name",
                        "args": {"key1": "new_value", "key2": "original_value"},
                    },
                }
            ]
        }
    ),
    config=config
)
```

---

### 7.4 ❌ reject (거절 + 피드백)
- `reject`는 실행을 거절하고, `message`를 대화에 피드백으로 추가한다.
- 이 피드백은 에이전트가 다음 행동을 수정하도록 유도한다.

```python
agent.invoke(
    Command(
        resume={
            "decisions": [
                {
                    "type": "reject",
                    "message": "이 작업은 허용되지 않습니다. 대신 ... 방식으로 처리하세요.",
                }
            ]
        }
    ),
    config=config
)
```

<br>

### 7.5 여러 액션이 동시에 중단된 경우 (Multiple Decisions)
- `decisions`는 **액션 개수만큼** 제공해야 한다.
- **순서가 중요**하며, interrupt에 나온 액션 순서대로 결정 리스트를 구성해야 한다.

```python
{
    "decisions": [
        {"type": "approve"},
        {
            "type": "edit",
            "edited_action": {
                "name": "tool_name",
                "args": {"param": "new_value"}
            }
        },
        {
            "type": "reject",
            "message": "이 작업은 허용되지 않습니다."
        }
    ]
}
```

<br>

## 8. Streaming에서의 HITL 사용 (stream)
- `invoke()` 대신 `stream()`으로 실행하면 에이전트 진행 상황/토큰을 실시간으로 받을 수 있다.
- `stream_mode=["updates", "messages"]`를 사용하면:
  - `messages`: LLM 토큰 스트리밍
  - `updates`: 상태 업데이트 및 interrupt 감지

### 8.1 interrupt까지 스트리밍
```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    stream_mode=["updates", "messages"],
):
    if mode == "messages":
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
    elif mode == "updates":
        if "__interrupt__" in chunk:
            print(f"\n\nInterrupt: {chunk['__interrupt__']}")
```

### 8.2 승인 후 재개(스트리밍)
```python
for mode, chunk in agent.stream(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
    stream_mode=["updates", "messages"],
):
    if mode == "messages":
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
```

<br>

## 9. 실행 라이프사이클(Execution Lifecycle)
HITL 미들웨어는 모델 응답 생성 이후, 툴 실행 전에 개입하는 훅(예: `after_model`)을 통해 동작한다.

1. 에이전트가 모델을 호출하여 응답 생성
2. 미들웨어가 모델 응답에서 툴 호출(tool call)들을 검사
3. `interrupt_on` 정책에 따라 사람 검토가 필요하면 `HITLRequest`를 구성하고 `interrupt` 발생
4. 실행이 중단되고 사람 결정을 기다림
5. 결정에 따라 처리:
   - approve/edit: 승인된(또는 수정된) 툴 호출 실행
   - reject: 거절된 호출에 대해서는 거절 메시지를 대화에 추가하는 형태로 처리(예: ToolMessage 생성)
6. 그래프 실행 재개

<br>

## 10. 커스텀 HITL 로직
- 더 특수한 워크플로우가 필요하면, 미들웨어 대신/또는 추가로 LangGraph의 `interrupt` 프리미티브와 미들웨어 추상화를 이용해 **커스텀 HITL 로직**을 직접 구현할 수 있다.
- 기본 동작을 이해하려면 “실행 라이프사이클” 흐름을 기준으로 통합 지점을 잡으면 된다.

<br>

## 11. 필드/옵션 요약
### 11.1 `HumanInTheLoopMiddleware` 주요 옵션
- `interrupt_on` (dict, 필수)
  - 툴 이름 → 승인 정책 매핑
  - 값:
    - `True`: 기본 interrupt
    - `False`: 자동 승인(중단 없음)
    - `InterruptOnConfig`(dict): 상세 정책(예: allowed_decisions, description)
- `description_prefix` (string, 선택)
  - interrupt 메시지 설명 앞부분(prefix)

### 11.2 `InterruptOnConfig`(dict) 옵션
- `allowed_decisions` (list[string])
  - 허용 결정 타입 목록: `"approve"`, `"edit"`, `"reject"`
- `description` (string 또는 callable)
  - interrupt 설명 커스터마이징

<br>

## 12. 한 줄 요약
- **HITL = “툴 실행 직전”에 정책 기반으로 실행을 멈추고, 사람의 승인/수정/거절로 안전하게 재개하는 미들웨어**
