"""SYNTRA model_runtime package.

Google Gen AI SDK adapters, router, cost/token ledger, and test doubles.
"""

from syntra.llm import (
    MODEL_REGISTRY,
    PROMPT_REGISTRY,
    AgentContextBuilder,
    GeminiModelProvider,
    MockModelProvider,
    ModelProvider,
    ModelRequest,
    ModelRouter,
    ModelRuntime,
    ModelRuntimeResult,
    ModelSpec,
    PromptRegistry,
    PromptTemplate,
    compute_token_cost,
    get_model_spec,
    get_role_prompt,
)

__all__ = [
    "ModelProvider",
    "ModelRequest",
    "GeminiModelProvider",
    "MockModelProvider",
    "ModelRuntime",
    "ModelRuntimeResult",
    "AgentContextBuilder",
    "ModelSpec",
    "MODEL_REGISTRY",
    "get_model_spec",
    "compute_token_cost",
    "PromptRegistry",
    "PROMPT_REGISTRY",
    "PromptTemplate",
    "get_role_prompt",
    "ModelRouter",
]
