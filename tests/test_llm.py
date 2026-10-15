"""Tests for SYNTRA LLM integration module."""

import pytest
from pydantic import BaseModel

from syntra.core.exceptions import LLMError
from syntra.llm import (
    GeminiClient,
    LLMMessage,
    MessageRole,
    MockLLMClient,
    ModelRouter,
    get_role_prompt,
)


class ArchitecturePlan(BaseModel):
    title: str
    modules: list[str]
    estimated_effort_days: int = 1


def test_model_router():
    assert "pro" in ModelRouter.resolve_model("architect")
    assert "pro" in ModelRouter.resolve_model("reviewer")
    assert "flash" in ModelRouter.resolve_model("coder")
    assert "flash" in ModelRouter.resolve_model("summarizer")
    assert ModelRouter.resolve_model(requested_model="custom-gemini") == "custom-gemini"


def test_role_prompts():
    assert "System Architect" in get_role_prompt("architect")
    assert "Senior Software Engineer" in get_role_prompt("coder")
    assert "Code Reviewer" in get_role_prompt("reviewer")
    assert "Test Automation Engineer" in get_role_prompt("tester")


@pytest.mark.asyncio
async def test_mock_llm_client_simple_response():
    client = MockLLMClient()
    client.queue_response("Hello from simulated Gemini!")

    messages = [LLMMessage(role=MessageRole.USER, content="Hello")]
    resp = await client.generate(messages, agent_role="coder")

    assert resp.text == "Hello from simulated Gemini!"
    assert resp.usage.total_tokens > 0
    assert len(client.call_history) == 1


@pytest.mark.asyncio
async def test_mock_llm_client_tool_call():
    client = MockLLMClient()
    client.queue_response(
        {
            "text": "I will inspect the workspace files.",
            "tool_calls": [{"id": "c1", "name": "list_files", "arguments": {"path": "."}}],
        }
    )

    messages = [LLMMessage(role=MessageRole.USER, content="List the project files")]
    resp = await client.generate(messages, agent_role="coder")

    assert "inspect" in resp.text
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "list_files"
    assert resp.tool_calls[0].arguments == {"path": "."}


@pytest.mark.asyncio
async def test_mock_llm_client_structured_generation():
    client = MockLLMClient()
    client.queue_response(
        ArchitecturePlan(
            title="SYNTRA Monolith",
            modules=["core", "llm", "sandbox", "agents"],
            estimated_effort_days=5,
        )
    )

    plan, resp = await client.generate_structured(
        messages=[LLMMessage(role=MessageRole.USER, content="Design architecture")],
        response_model=ArchitecturePlan,
    )

    assert plan.title == "SYNTRA Monolith"
    assert len(plan.modules) == 4
    assert plan.estimated_effort_days == 5


def test_gemini_client_unconfigured_error():
    client = GeminiClient(api_key=None)
    with pytest.raises(LLMError):
        client._ensure_client()
