"""
tasks.py — run_experiment() 용 task function 팩토리

make_task(rag_config, db_connection) → 동기 task 함수 반환
task 함수 시그니처: (example: dict) -> {"answer": str, "retrieved_context": str}

example 구조:
  example["input"]["question"] : 질문 텍스트
  example["input"]["doc_id"]   : 검색 필터용 doc_id
"""

import asyncio
import concurrent.futures
from typing import Any, Optional

from langchain_core.messages import ToolMessage

from agent import ChatAgent, PROMPT_KEYS
from embeddings import EmbeddingModel
from tool import ToolBuilder
from vector_store import VectorStoreManager
from prompt_loader import get_prompt
from eval.configs import RAGConfig


def extract_context_from_messages(messages: list) -> str:
    """에이전트 메시지 목록에서 첫 번째 ToolMessage content를 반환한다."""
    for msg in messages:
        if isinstance(msg, ToolMessage):
            return msg.content or ""
    return ""


def build_system_prompt_with_override(prompt_override: dict[str, str]) -> str:
    """Redis에서 프롬프트를 로드하되 override 딕셔너리의 키로 교체한다."""
    parts = []
    for key in PROMPT_KEYS:
        if key in prompt_override:
            p = prompt_override[key]
        else:
            p = get_prompt(key)
        if p:
            parts.append(p)
    return "\n\n".join(parts)


def make_task(rag_config: RAGConfig, db_connection: str):
    """RAGConfig 기반으로 task function을 생성한다.

    반환된 task 함수는 run_experiment()에 직접 전달할 수 있다.
    각 호출마다 새로운 VectorStoreManager와 ChatAgent를 초기화한다.
    """

    def task(example: dict) -> dict:
        question: str = example["input"]["question"]
        doc_id: Optional[str] = example["input"].get("doc_id")

        async def _run() -> dict:
            embedding_model = EmbeddingModel().get_embeddings()
            vsm = await VectorStoreManager.create(
                connection_string=db_connection,
                embedding_model=embedding_model,
            )

            tool_builder = ToolBuilder(vsm)
            tools = tool_builder.build_tools(
                doc_ids=[doc_id] if doc_id else None,
                k=rag_config.retrieval_k,
            )

            if rag_config.prompt_override is not None:
                system_prompt: Optional[str] = build_system_prompt_with_override(
                    rag_config.prompt_override
                )
            else:
                system_prompt = None  # ChatAgent가 Redis에서 로드

            agent = ChatAgent(
                model_name=rag_config.model_name,
                system_prompt=system_prompt,
            )
            agent.create_agent(tools)

            final_messages: list = []
            async for event in agent.agent.astream(
                {"messages": [{"role": "user", "content": question}]},
                stream_mode="values",
            ):
                final_messages = event["messages"]

            answer = final_messages[-1].content if final_messages else ""
            retrieved_context = extract_context_from_messages(final_messages)

            return {"answer": answer, "retrieved_context": retrieved_context}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(asyncio.run, _run()).result()
        return asyncio.run(_run())

    return task
