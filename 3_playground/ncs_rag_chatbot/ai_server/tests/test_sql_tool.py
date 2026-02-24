import json
import pytest
from unittest.mock import AsyncMock


async def test_query_employee_data_returns_json():
    from clients.spring.v1.employee import EmployeeClientV1
    from tools.sql_tool import SqlToolBuilder

    mock_client = AsyncMock(spec=EmployeeClientV1)
    mock_client.get_history.return_value = {
        "employee": {"employeeId": "EMP001", "name": "홍길동"},
        "educationHistory": [{"courseName": "Python 기초", "score": 95.0}],
        "assignmentSubmissions": [],
        "gradingResults": [],
    }

    builder = SqlToolBuilder(employee_client=mock_client)
    tools = builder.build_tools()
    assert len(tools) == 1

    tool = tools[0]
    result = await tool.ainvoke({"identifier": "EMP001"})
    data = json.loads(result)
    assert data["employee"]["name"] == "홍길동"
    assert data["educationHistory"][0]["score"] == 95.0
    mock_client.get_history.assert_called_once_with("EMP001")


async def test_query_employee_data_handles_api_error():
    import httpx
    from clients.spring.v1.employee import EmployeeClientV1
    from tools.sql_tool import SqlToolBuilder

    mock_client = AsyncMock(spec=EmployeeClientV1)
    mock_client.get_history.side_effect = httpx.HTTPStatusError(
        "404", request=AsyncMock(), response=AsyncMock()
    )

    builder = SqlToolBuilder(employee_client=mock_client)
    tools = builder.build_tools()
    result = await tools[0].ainvoke({"identifier": "INVALID"})
    assert "조회 실패" in result
