# ai_server/tests/test_config.py
import os
from unittest.mock import patch

def test_settings_default_values():
    from config import Settings
    s = Settings()
    assert s.spring_base_url == "http://localhost:8080"
    assert s.redis_port == 6379
    assert s.model_name == "gpt-4o-mini"
    assert s.spring_api_version == "v1"

def test_settings_from_env():
    with patch.dict(os.environ, {"SPRING_BASE_URL": "http://spring:8080"}):
        from config import Settings
        s = Settings()
        assert s.spring_base_url == "http://spring:8080"


def test_ingest_table_name_is_same_object_as_vector_store():
    """ingest.py의 TABLE_NAME은 vector_store.py에서 re-import된 동일 객체임을 검증한다.

    단순히 값이 같은 것(==)이 아니라 동일 객체(is)여야 단일 소스가 보장된다.
    ingest.py가 TABLE_NAME을 직접 정의하면 이 테스트는 실패한다.
    """
    from infra.vector_store import TABLE_NAME as vs_name
    from infra.ingest import TABLE_NAME as ingest_name
    assert vs_name is ingest_name
