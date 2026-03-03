from ai_server.tools.sql_tools import query_return_history


async def return_history_node(state: dict) -> dict:
    """반송이력 서브에이전트: return_history 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_return_history(product_id)
    return {"return_history_result": rows}
