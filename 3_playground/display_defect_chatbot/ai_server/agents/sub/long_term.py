import asyncio
from uuid import uuid4

from ai_server.agents.state import SubAgentInput
from ai_server.tools.sql_tools import (
    query_long_term_history,
    insert_bg_task,
    complete_bg_task,
    fail_bg_task,
)
from ai_server.infra.email_utils import send_completion_email

# asyncio.create_task 참조 유지 (GC로 인한 묵시적 취소 방지)
_background_tasks: set[asyncio.Task] = set()


async def long_term_node(state: SubAgentInput) -> dict:
    """장기이력 에이전트: 백그라운드로 실행, 즉시 task_id 반환"""
    task_id = str(uuid4())
    notify_email = state.get("notify_email")
    print(f"[LONG_TERM] 노드 시작 — task_id={task_id}, notify_email={notify_email!r}")

    await insert_bg_task(task_id, state["session_id"])

    task = asyncio.create_task(
        _run_long_term_analysis(
            task_id,
            state["product_id"],
            state["selected_hypothesis"],
            notify_email,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return {"long_term_task_id": task_id}


async def _run_long_term_analysis(
    task_id: str,
    product_id: str,
    hypothesis: str,
    notify_email: str | None = None,
):
    """장기 이력 분석 실행 (수 초 ~ 수십 초 소요 시뮬레이션)"""
    await asyncio.sleep(10)  # Mock: 실제 분석 시간 시뮬레이션

    result_text = None
    try:
        result_text = await query_long_term_history(product_id)
        # 가설 문자열 끝의 마침표 제거 후 조사 연결 (예: "...결함." + "를" → "...결함을")
        hyp_clean = hypothesis.rstrip(".").rstrip("。")
        result_text += (
            f"\n\n[가설 기반 추가 분석]\n"
            f"'{hyp_clean}'을(를) 중심으로 최근 6개월 불량 추이를 분석한 결과, "
            f"동일 원인에 의한 반복 발생 패턴이 확인되었습니다. "
            f"재발 방지를 위해 해당 공정 파라미터의 조정 및 지속적인 모니터링을 권고합니다."
        )
        print(f"[LONG_TERM] query 성공 — result_text 길이={len(result_text)}")
    except Exception as e:
        print(f"[LONG_TERM] query 실패 — {e}")

    if result_text is not None:
        await complete_bg_task(task_id, result_text)
        print(f"[LONG_TERM] complete_bg_task 완료 — notify_email={notify_email!r}")
        if notify_email:
            await send_completion_email(notify_email, product_id, result_text)
        else:
            print("[LONG_TERM] notify_email 없음 — 이메일 skip")
    else:
        print("[LONG_TERM] result_text=None — fail_bg_task 호출")
        await fail_bg_task(task_id)
