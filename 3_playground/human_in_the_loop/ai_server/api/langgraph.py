import uuid
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from langgraph.types import Command
from semiconductor.graph import graph

router = APIRouter()

# ─── Request / Response Models ─────────────────────────────

class RunStreamRequest(BaseModel):
    assistant_id: str = "agent"
    input: Optional[dict] = None
    config: dict = Field(default_factory=dict)
    stream_mode: list[str] = Field(default_factory=lambda: ["updates"])
    command: Optional[dict] = None


# ─── Helper: safe JSON serializer ──────────────────────────

class SafeEncoder(json.JSONEncoder):
    """Fallback encoder for LangChain/LangGraph objects."""
    def default(self, o):
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        if hasattr(o, 'dict'):
            return o.dict()
        if hasattr(o, '__dict__'):
            return {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
        return str(o)


def safe_dumps(obj):
    return json.dumps(obj, ensure_ascii=False, cls=SafeEncoder)


def extract_interrupt_value(interrupt_obj):
    """Interrupt 객체에서 value를 안전하게 추출."""
    if hasattr(interrupt_obj, 'value'):
        return interrupt_obj.value
    if isinstance(interrupt_obj, dict):
        return interrupt_obj
    return str(interrupt_obj)


# ─── Endpoints ─────────────────────────────────────────────

@router.post("/threads")
async def create_thread():
    thread_id = str(uuid.uuid4())
    return {"thread_id": thread_id}


@router.get("/threads/{thread_id}/state")
async def get_thread_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = graph.get_state(config)
        values = state.values if state.values else {}
        # values를 SafeEncoder로 직렬화 가능하게
        values = json.loads(safe_dumps(values))
        return {
            "values": values,
            "next": list(state.next) if state.next else [],
        }
    except Exception:
        return {"values": {}, "next": []}


@router.post("/threads/{thread_id}/runs/stream")
async def stream_run(thread_id: str, body: RunStreamRequest):
    config = {"configurable": {"thread_id": thread_id}}
    if body.config:
        config["configurable"].update(body.config.get("configurable", {}))

    async def event_generator():
        try:
            # resume vs initial run
            if body.command and body.command.get("resume") is not None:
                stream_input = Command(resume=body.command["resume"])
            elif body.input:
                stream_input = body.input
            else:
                yield f"event: error\ndata: {safe_dumps({'error': 'No input or command provided'})}\n\n"
                return

            async for chunk in graph.astream(
                stream_input,
                config=config,
                stream_mode="updates",
            ):
                # chunk: {"node_name": {...}} or {"__interrupt__": [Interrupt(...)]}
                if "__interrupt__" in chunk:
                    # __interrupt__는 Interrupt 객체 리스트 → value만 추출
                    interrupts = chunk["__interrupt__"]
                    interrupt_data = [extract_interrupt_value(i) for i in interrupts]
                    yield f"event: updates\ndata: {safe_dumps({'__interrupt__': interrupt_data})}\n\n"
                else:
                    # 일반 노드 업데이트
                    yield f"event: updates\ndata: {safe_dumps(chunk)}\n\n"

            yield "event: end\ndata: {}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {safe_dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/assistants/search")
async def search_assistants():
    return [
        {
            "assistant_id": "agent",
            "graph_id": "agent",
            "name": "Semiconductor Agent",
        }
    ]
