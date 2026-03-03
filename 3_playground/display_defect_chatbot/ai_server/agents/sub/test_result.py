from ai_server.tools.sql_tools import query_test_results


async def test_result_node(state: dict) -> dict:
    """테스트결과 서브에이전트: test_results 테이블 조회"""
    product_id = state.get("product_id", "")
    rows = await query_test_results(product_id)
    return {"test_result": rows}
