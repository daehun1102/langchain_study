"""
sql_tool.py — 직원 이력 조회 Tool (thin wrapper)

실제 HTTP 호출은 clients/spring/v1/employee.py 에 위임한다.
"""
import json
import logging
from typing import List

from langchain.tools import tool
from langchain_core.tools import Tool

logger = logging.getLogger("sql_tool")


class SqlToolBuilder:

    def __init__(self, employee_client):
        self._client = employee_client

    def build_tools(self) -> List[Tool]:
        _client = self._client

        @tool
        async def query_employee_data(identifier: str) -> str:
            """직원의 교육 이수 내역, 과제 제출, 채점 결과를 조회한다.

            Args:
                identifier: 사번(예: EMP001) 또는 직원 이름(예: 홍길동)
            Returns:
                JSON 형식의 직원 이력 데이터
            """
            try:
                result = await _client.get_history(identifier)
                return json.dumps(result, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error("[sql_tool] 직원 이력 조회 실패: %s", e)
                return f"직원 이력 조회 실패: {identifier} — {e}"

        return [query_employee_data]
