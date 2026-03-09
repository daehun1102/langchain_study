# display_defect_chatbot/ai_server/infra/graph_logger.py
"""
LangGraph StateGraph 노드용 커스텀 미들웨어.

langchain.agents.middleware 의 AgentMiddleware 패턴을 참고하여
커스텀 StateGraph 노드에 before_node / after_node / on_node_error 훅을 제공.

설정 (.env):
    LOG_GRAPH_ENABLED  = true | false        (기본: false)
    LOG_GRAPH_TARGET   = console | file | both   (기본: console)
    LOG_GRAPH_FILE     = logs/graph.log      (file/both 일 때 경로)
    LOG_GRAPH_LEVEL    = DEBUG | INFO | WARNING   (기본: INFO)

사용:
    # graph.py 에서 노드 등록 시 apply_middleware() 로 래핑
    middleware = build_node_middleware(settings)
    builder.add_node("my_node", apply_middleware(my_node_fn, "my_node", middleware))
"""

import json
import logging
import os
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable

_SEP = "━" * 56


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _truncate(value: Any, max_len: int = 120) -> str:
    """값을 JSON 문자열로 변환 후 max_len 초과 시 말줄임"""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    return text if len(text) <= max_len else text[:max_len] + " …"


def _fmt_value(value: Any) -> str:
    """AgentAnalysisResult는 건수+분석 요약, 리스트는 건수, 나머지는 truncate"""
    if isinstance(value, dict) and "suspect_rows" in value:
        rows = value.get("suspect_rows") or []
        analysis = _truncate(value.get("analysis", ""), 60)
        return f"{len(rows)}건 │ {analysis}"
    if isinstance(value, list):
        return f"{len(value)}건"
    return _truncate(value, 80)


def _fmt_fields(data: dict[str, Any]) -> list[str]:
    return [
        f"  {k:<26}: {_fmt_value(v)}"
        for k, v in data.items()
        if v is not None and v != "" and v != []
    ]


# ── 미들웨어 베이스 클래스 ───────────────────────────────────────────────────

class GraphNodeMiddleware:
    """
    LangGraph StateGraph 노드용 미들웨어 베이스 클래스.

    AgentMiddleware 패턴을 참고: 필요한 훅만 오버라이드.
    - before_node : 노드 실행 직전
    - after_node  : 노드 정상 완료 후
    - on_node_error : 노드 실행 중 예외 발생 시
    """

    def before_node(self, node_name: str, state: dict[str, Any]) -> None:
        """노드 실행 직전에 호출됩니다."""
        ...

    def after_node(self, node_name: str, output: dict[str, Any]) -> None:
        """노드가 정상 완료된 직후에 호출됩니다."""
        ...

    def on_node_error(self, node_name: str, error: BaseException) -> None:
        """노드 실행 중 예외 발생 시 호출됩니다."""
        ...


# ── 구현체 ───────────────────────────────────────────────────────────────────

class StateLoggingMiddleware(GraphNodeMiddleware):
    """노드 입력·출력 상태를 블록 형식으로 로깅하는 미들웨어 구현체."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._start_times: dict[str, float] = {}

    def before_node(self, node_name: str, state: dict[str, Any]) -> None:
        self._start_times[node_name] = time.monotonic()
        ts = datetime.now().strftime("%H:%M:%S")
        lines = [_SEP, f"▶ NODE START │ {node_name:<30} │ {ts}"] + _fmt_fields(state)
        self._logger.info("\n".join(lines))

    def after_node(self, node_name: str, output: dict[str, Any]) -> None:
        elapsed = time.monotonic() - self._start_times.pop(node_name, 0.0)
        ts = datetime.now().strftime("%H:%M:%S")
        lines = [f"◀ NODE DONE  │ {node_name:<30} │ {ts}  +{elapsed:.2f}s"] + _fmt_fields(output) + [_SEP]
        self._logger.info("\n".join(lines))

    def on_node_error(self, node_name: str, error: BaseException) -> None:
        elapsed = time.monotonic() - self._start_times.pop(node_name, 0.0)
        ts = datetime.now().strftime("%H:%M:%S")
        lines = [
            f"✗ NODE ERROR │ {node_name:<30} │ {ts}  +{elapsed:.2f}s",
            f"  {type(error).__name__}: {error}",
            _SEP,
        ]
        self._logger.error("\n".join(lines))


class NullMiddleware(GraphNodeMiddleware):
    """로깅 비활성화 시 사용하는 no-op 미들웨어 (오버헤드 없음)"""


# ── apply_middleware ─────────────────────────────────────────────────────────

def apply_middleware(
    node_fn: Callable,
    node_name: str,
    middleware: GraphNodeMiddleware,
) -> Callable:
    """
    노드 함수에 미들웨어 훅을 감싸서 반환.

    AgentMiddleware 의 wrap_model_call 패턴에 대응:
        handler(request) 호출 전후로 before/after 훅 실행.

    Args:
        node_fn    : 원본 노드 async 함수
        node_name  : 로그에 표시할 노드 이름
        middleware : GraphNodeMiddleware 인스턴스
    """
    @wraps(node_fn)
    async def wrapped(state: dict[str, Any], **kwargs) -> dict[str, Any]:
        middleware.before_node(node_name, state)
        try:
            result = await node_fn(state, **kwargs)
        except BaseException as e:
            middleware.on_node_error(node_name, e)
            raise
        middleware.after_node(node_name, result)
        return result

    return wrapped


# ── 팩토리 ───────────────────────────────────────────────────────────────────

def _build_logger(target: str, file_path: str, level: str) -> logging.Logger:
    """핸들러가 붙은 Python Logger 반환 (내부 헬퍼)"""
    logger = logging.getLogger("graph.state")
    logger.propagate = False
    logger.handlers.clear()

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    fmt = logging.Formatter("%(message)s")

    if target in ("console", "both"):
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    if target in ("file", "both"):
        log_dir = os.path.dirname(file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def build_node_middleware(settings) -> GraphNodeMiddleware:
    """
    settings 값에 따라 적절한 미들웨어 인스턴스를 반환.

    LOG_GRAPH_ENABLED=false  → NullMiddleware (no-op)
    LOG_GRAPH_ENABLED=true   → StateLoggingMiddleware
    """
    if not settings.log_graph_enabled:
        return NullMiddleware()

    logger = _build_logger(
        target=settings.log_graph_target,
        file_path=settings.log_graph_file,
        level=settings.log_graph_level,
    )
    return StateLoggingMiddleware(logger)
