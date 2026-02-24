import httpx
from config import settings


class SpringClient:
    """Spring Boot API 공통 httpx 클라이언트."""

    def __init__(self, base_url: str = None, timeout: float = 10.0):
        self.base_url = base_url or settings.spring_base_url
        self.timeout = timeout

    def build(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
