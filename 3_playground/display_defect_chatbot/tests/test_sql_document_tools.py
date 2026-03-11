# tests/test_sql_document_tools.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ai_server.tools.sql_tools import list_documents, insert_document, delete_document


@pytest.mark.asyncio
async def test_list_documents_returns_list():
    mock_rows = [
        {"doc_id": "abc", "filename": "a.txt", "doc_type": "txt", "status": "INDEXED", "created_at": "2026-01-01"},
    ]
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await list_documents()
        assert result == mock_rows


@pytest.mark.asyncio
async def test_insert_document_returns_row():
    inserted = {"doc_id": "abc", "filename": "a.txt", "doc_type": "txt", "status": "INDEXED", "created_at": "2026-01-01"}
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = inserted
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await insert_document("abc", "a.txt", "txt", "INDEXED")
        assert result["doc_id"] == "abc"
        assert result["filename"] == "a.txt"


@pytest.mark.asyncio
async def test_delete_document_executes():
    with patch("ai_server.tools.sql_tools.get_db_session") as mock_ctx:
        mock_session = AsyncMock()
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

        await delete_document("abc")
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0]  # positional args tuple
        assert call_args[1] == {"doc_id": "abc"}
