import sys
import os
from unittest.mock import MagicMock

# ai_server/ 를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Mock external packages that are not installed in the test environment.
# These must be injected into sys.modules BEFORE any ai_server module is imported,
# because prompt_loader.py, embeddings.py, and vector_store.py import them at
# module load time.
_MISSING_MODULES = [
    "redis",
    "langchain_openai",
    "langchain_postgres",
    "dotenv",
]
for _mod in _MISSING_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
