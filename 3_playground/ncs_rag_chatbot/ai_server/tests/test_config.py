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
