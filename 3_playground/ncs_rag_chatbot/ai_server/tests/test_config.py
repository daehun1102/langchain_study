# ai_server/tests/test_config.py
import os
from unittest.mock import patch

def test_settings_default_values():
    from config import settings
    assert settings.spring_base_url == "http://localhost:8080"
    assert settings.redis_port == 6379
    assert settings.model_name == "gpt-4o-mini"
    assert settings.spring_api_version == "v1"

def test_settings_from_env():
    with patch.dict(os.environ, {"SPRING_BASE_URL": "http://spring:8080"}):
        import importlib, config
        importlib.reload(config)
        from config import settings
        assert settings.spring_base_url == "http://spring:8080"
