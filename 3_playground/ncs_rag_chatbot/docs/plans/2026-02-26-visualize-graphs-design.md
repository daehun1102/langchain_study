# Agent Graph 시각화 설계

**Goal:** v1(SupervisorAgent), v2(NCSHandoffAgent) 의 LangGraph 그래프 구조를 PNG로 저장한다.

**Architecture:**
- 두 에이전트 모두 `create_agent()` (= `create_react_agent` 래퍼)를 사용 → LangGraph 컴파일 그래프 반환
- 그래프 구조는 API 키 없이 빌드 가능 (실행 시에만 API 호출 발생)
- `get_graph().draw_mermaid_png()` → Mermaid.ink 외부 API → PNG bytes

**Output:**
- `docs/v1_graph.png` — SupervisorAgent (표준 ReAct)
- `docs/v2_graph.png` — NCSHandoffAgent (커스텀 state + middleware ReAct)

**실행:** `cd ai_server && python ../scripts/visualize_graphs.py`

**Tech:** Python 스크립트 1개, 추가 패키지 불필요 (langgraph 이미 설치됨)
