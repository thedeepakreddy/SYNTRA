"""SYNTRA LLM and Model Runtime Module.

Provides provider-independent LLM runtime, official Google Gemini SDK integration,
deterministic mock provider, versioned prompt management, progressive skill context,
and MCP Tool Gateway integration.
"""

from syntra.llm.client import BaseLLMClient, GeminiClient
from syntra.llm.config import (
    MODEL_REGISTRY,
    ModelSpec,
    ModelTier,
    PricingConfiguration,
    UnknownCostPolicy,
    compute_token_cost,
    get_model_spec,
    load_model_registry,
)
from syntra.llm.context import AgentContextBuilder
from syntra.llm.exceptions import (
    ModelAuthenticationError,
    ModelBudgetExceededError,
    ModelOutputValidationError,
    ModelPricingError,
    ModelProviderUnavailableError,
    ModelQuotaExceededError,
    ModelRetryExhaustedError,
    ModelRuntimeError,
    ModelTimeoutError,
    ModelToolExecutionError,
)
from syntra.llm.gemini_provider import GeminiModelProvider
from syntra.llm.mock import MockLLMClient
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.models import (
    LLMMessage,
    LLMResponse,
    MessageRole,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from syntra.llm.prompts import (
    ARCHITECT_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    COORDINATOR_SYSTEM_PROMPT,
    PLANNER_SYSTEM_PROMPT,
    PROMPT_REGISTRY,
    REVIEWER_SYSTEM_PROMPT,
    ROLE_PROMPTS,
    SECURITY_SYSTEM_PROMPT,
    TESTER_SYSTEM_PROMPT,
    PromptRegistry,
    PromptTemplate,
    get_role_prompt,
)
from syntra.llm.provider import ModelProvider, ModelRequest
from syntra.llm.router import ModelRouter
from syntra.llm.runtime import ModelRuntime, ModelRuntimeResult
from syntra.llm.schemas import (
    AgentFinalResult,
    AgentToolAction,
    ArchitectureProposal,
    CodeReviewComment,
    CodeReviewProposal,
    FailureAnalysis,
    RequirementsAnalysis,
    TaskPlanItem,
    TaskPlanProposal,
)

__all__ = [
    # Core Interfaces
    "ModelProvider",
    "ModelRequest",
    "BaseLLMClient",
    "GeminiClient",
    "GeminiModelProvider",
    "MockLLMClient",
    "MockModelProvider",
    "ModelRuntime",
    "ModelRuntimeResult",
    "AgentContextBuilder",
    # Structured Output Schemas (Task 3)
    "RequirementsAnalysis",
    "ArchitectureProposal",
    "TaskPlanItem",
    "TaskPlanProposal",
    "AgentToolAction",
    "AgentFinalResult",
    "FailureAnalysis",
    "CodeReviewComment",
    "CodeReviewProposal",
    # Data Models
    "LLMMessage",
    "LLMResponse",
    "MessageRole",
    "ToolCall",
    "ToolDefinition",
    "ToolResult",
    "ModelTier",
    "ModelSpec",
    "PricingConfiguration",
    "UnknownCostPolicy",
    "MODEL_REGISTRY",
    "load_model_registry",
    "get_model_spec",
    "compute_token_cost",
    # Prompts & Routing
    "ModelRouter",
    "PromptTemplate",
    "PromptRegistry",
    "PROMPT_REGISTRY",
    "get_role_prompt",
    "ROLE_PROMPTS",
    "ARCHITECT_SYSTEM_PROMPT",
    "PLANNER_SYSTEM_PROMPT",
    "CODER_SYSTEM_PROMPT",
    "REVIEWER_SYSTEM_PROMPT",
    "TESTER_SYSTEM_PROMPT",
    "SECURITY_SYSTEM_PROMPT",
    "COORDINATOR_SYSTEM_PROMPT",
    # Exceptions
    "ModelRuntimeError",
    "ModelAuthenticationError",
    "ModelQuotaExceededError",
    "ModelTimeoutError",
    "ModelRetryExhaustedError",
    "ModelOutputValidationError",
    "ModelToolExecutionError",
    "ModelProviderUnavailableError",
    "ModelBudgetExceededError",
    "ModelPricingError",
]
