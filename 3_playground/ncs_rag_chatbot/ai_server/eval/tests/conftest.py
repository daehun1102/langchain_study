import sys
import os
from unittest.mock import MagicMock

# ai_server/ 를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Mock external packages that are not installed in the test environment.
# These must be injected into sys.modules BEFORE any ai_server module is imported,
# because they are imported at module load time through these chains:
#   - embeddings.py, vector_store.py → langchain_openai
#   - prompt_loader.py → redis
#   - infra/ingest.py → langchain_postgres, dotenv
#   - infra/loader.py → langchain_upstage (+ langchain_openai submodules)
_MISSING_MODULES = [
    "redis",
    "langchain_openai",
    "langchain_openai.chat_models",
    "langchain_openai.chat_models.base",
    "langchain_postgres",
    "dotenv",
    "langchain_upstage",
]
for _mod in _MISSING_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
