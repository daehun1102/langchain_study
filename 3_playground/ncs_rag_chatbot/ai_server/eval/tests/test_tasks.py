from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from eval.configs import RAGConfig, V1_BASELINE
from eval.tasks import make_task, extract_context_from_messages, build_system_prompt_with_override


# ── extract_context_from_messages tests ─────────────────────────

def test_extract_context_returns_tool_message_content():
    """ToolMessage가 있으면 content를 반환한다."""
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

    messages = [
        HumanMessage(content="질문"),
        AIMessage(content="", tool_calls=[]),
        ToolMessage(content="검색된 컨텍스트 내용", tool_call_id="id1"),
        AIMessage(content="최종 답변"),
    ]
    result = extract_context_from_messages(messages)
    assert result == "검색된 컨텍스트 내용"


def test_extract_context_returns_empty_when_no_tool_message():
    """ToolMessage가 없으면 빈 문자열을 반환한다."""
    from langchain_core.messages import HumanMessage, AIMessage

    messages = [HumanMessage(content="질문"), AIMessage(content="답변")]
    result = extract_context_from_messages(messages)
    assert result == ""


# ── build_system_prompt_with_override tests ──────────────────────

def test_build_system_prompt_override_replaces_specific_key():
    """prompt_override의 특정 키가 Redis 값 대신 사용된다."""
    mock_get_prompt = MagicMock(return_value="redis_value")
    override = {"agent_system_prompt": "custom_system_prompt"}

    with patch("eval.tasks.get_prompt", mock_get_prompt):
        result = build_system_prompt_with_override(override)

    assert "custom_system_prompt" in result
    assert "redis_value" in result


def test_build_system_prompt_override_skips_empty_parts():
    """빈 문자열 프롬프트는 결합에서 제외된다."""
    def mock_get_prompt(key):
        return "" if key == "category_hint_prompt" else "value"

    override = {}
    with patch("eval.tasks.get_prompt", mock_get_prompt):
        result = build_system_prompt_with_override(override)

    assert "value" in result
    # Empty parts should not create double newlines
    assert "\n\n\n" not in result


# ── make_task factory tests ──────────────────────────────────────

def test_make_task_returns_callable():
    task = make_task(V1_BASELINE, db_connection="postgresql+asyncpg://test")
    assert callable(task)


def test_make_task_output_has_required_keys():
    """task 함수가 answer와 retrieved_context를 반환한다."""
    from langchain_core.messages import AIMessage, ToolMessage

    mock_messages = [
        ToolMessage(content="검색된 컨텍스트", tool_call_id="id1"),
        AIMessage(content="에이전트 최종 답변"),
    ]
    mock_event = {"messages": mock_messages}

    async def mock_astream(*args, **kwargs):
        yield mock_event

    with patch("eval.tasks.VectorStoreManager") as mock_vsm_cls, \
         patch("eval.tasks.EmbeddingModel") as mock_emb_cls, \
         patch("eval.tasks.ToolBuilder") as mock_tb_cls, \
         patch("eval.tasks.ChatAgent") as mock_agent_cls:

        mock_vsm = AsyncMock()
        mock_vsm_cls.create = AsyncMock(return_value=mock_vsm)
        mock_emb_cls.return_value.get_embeddings.return_value = MagicMock()
        mock_tb_cls.return_value.build_tools.return_value = []

        mock_agent_instance = MagicMock()
        mock_agent_instance.agent.astream = mock_astream
        mock_agent_cls.return_value = mock_agent_instance

        task = make_task(V1_BASELINE, db_connection="postgresql+asyncpg://test")
        example = {"input": {"question": "테스트 질문", "doc_id": "uuid-001"}}
        result = task(example)

    assert "answer" in result
    assert "retrieved_context" in result
    assert result["answer"] == "에이전트 최종 답변"
    assert result["retrieved_context"] == "검색된 컨텍스트"
