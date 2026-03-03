from ai_server.tools.sql_tools import query_process_history


async def process_history_node(state: dict) -> dict:
    """공정이력 서브에이전트: process_history 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_process_history(product_id)
    return {"process_history_result": rows}
