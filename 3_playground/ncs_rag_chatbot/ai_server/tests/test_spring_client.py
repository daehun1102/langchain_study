import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


async def test_get_history_returns_employee_data():
    from clients.spring.v1.employee import EmployeeClientV1

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "employee": {"employeeId": "EMP001", "name": "홍길동"},
        "educationHistory": [],
        "assignmentSubmissions": [],
        "gradingResults": [],
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        client = EmployeeClientV1(base_url="http://localhost:8080")
        result = await client.get_history("EMP001")

    assert result["employee"]["name"] == "홍길동"
    assert "educationHistory" in result


async def test_get_history_raises_on_http_error():
    from clients.spring.v1.employee import EmployeeClientV1

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock()
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        client = EmployeeClientV1(base_url="http://localhost:8080")
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_history("INVALID")
