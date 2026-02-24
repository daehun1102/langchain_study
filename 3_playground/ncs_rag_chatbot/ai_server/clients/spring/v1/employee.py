from typing import Any


class EmployeeClientV1:
    """직원 이력 API v1 클라이언트."""

    def __init__(self, base_url: str = None):
        from clients.spring.base import SpringClient
        self._spring = SpringClient(base_url=base_url)

    async def get_history(self, identifier: str) -> dict[str, Any]:
        """사번 또는 이름으로 직원 교육 이수/과제/채점 이력을 조회한다."""
        async with self._spring.build() as client:
            resp = await client.get(
                "/internal/v1/employee/history",
                params={"identifier": identifier},
            )
            resp.raise_for_status()
            return resp.json()
