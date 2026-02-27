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


def test_ingest_uses_same_table_name_as_vector_store():
    """ingest.py와 vector_store.py는 동일한 TABLE_NAME을 사용한다."""
    from infra.vector_store import TABLE_NAME as vs_name
    from infra.ingest import TABLE_NAME as ingest_name
    assert vs_name == ingest_name
