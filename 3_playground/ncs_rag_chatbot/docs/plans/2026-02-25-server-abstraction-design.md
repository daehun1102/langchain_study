# server.py 추상화 설계 — 패키지 인터페이스 의존

**Goal:** `server.py`가 버전(`v1`) 경로를 직접 import하지 않고 패키지 레벨 인터페이스에만 의존하도록 수정한다.

---

## 문제

`server.py`가 구현체의 버전 경로를 직접 참조하고 있다:

```python
from agents.v1.rag_agent import ChatAgent       # v1 직접 노출
from agents.v1.sql_agent import SqlAgent
from agents.v1.supervisor import SupervisorAgent
from tools.rag_tool import ToolBuilder           # 구현 파일명 직접 노출
from clients.spring.v1.employee import EmployeeClientV1  # v1 직접 노출
```

향후 `v2`로 교체 시 `server.py`도 함께 수정해야 하는 결합이 발생한다.

---

## 해결

각 패키지의 `__init__.py`가 이미 올바른 re-export를 제공하고 있으므로,
`server.py`의 import만 패키지 레벨로 올린다.

| 패키지 | `__init__.py` 상태 |
|--------|-------------------|
| `agents/__init__.py` | `ChatAgent`, `SqlAgent`, `SupervisorAgent` re-export ✅ |
| `tools/__init__.py` | `ToolBuilder` re-export ✅ |
| `clients/spring/__init__.py` | `EmployeeClientV1` re-export ✅ |

---

## 변경 내용

**`ai_server/server.py` — import 3줄 교체:**

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

---

## 원칙

- `server.py`는 `agents`, `tools`, `clients.spring` 패키지가 공개 API로 제공하는 이름만 사용한다.
- 버전 변경(`v1` → `v2`)은 각 패키지의 `__init__.py`만 수정하면 되며, `server.py`는 무관하다.
- 추가 코드(팩토리, DI 컨테이너 등) 없이 기존 re-export 구조를 활용한다.
