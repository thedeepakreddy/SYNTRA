"""Model routing and tier selection based on agent role and task complexity."""

from syntra.core.config import get_settings
from syntra.llm.config import ModelTier


class ModelRouter:
    """Routes agent requests to the most appropriate Gemini model."""

    ROLE_DEFAULTS: dict[str, ModelTier] = {
        # AGENTS.md canonical roles
        "product_manager": ModelTier.REASONING,
        "software_architect": ModelTier.REASONING,
        "engineering_manager": ModelTier.REASONING,
        "backend_engineer": ModelTier.BALANCED,
        "frontend_engineer": ModelTier.BALANCED,
        "qa_engineer": ModelTier.BALANCED,
        "devops_engineer": ModelTier.BALANCED,
        "security_reviewer": ModelTier.REASONING,
        "code_reviewer": ModelTier.REASONING,
        "debugging_specialist": ModelTier.BALANCED,
        # Short aliases
        "architect": ModelTier.REASONING,
        "pm": ModelTier.REASONING,
        "em": ModelTier.REASONING,
        "planner": ModelTier.REASONING,
        "security": ModelTier.REASONING,
        "coder": ModelTier.BALANCED,
        "reviewer": ModelTier.REASONING,
        "tester": ModelTier.BALANCED,
        "devops": ModelTier.BALANCED,
        "debugger": ModelTier.BALANCED,
        "coordinator": ModelTier.BALANCED,
        "summarizer": ModelTier.FAST,
        "triage": ModelTier.FAST,
    }

    @classmethod
    def resolve_model(
        cls,
        agent_role: str | None = None,
        requested_model: str | None = None,
        is_complex: bool = False,
    ) -> str:
        """Resolve model name string."""
        if requested_model:
            return requested_model

        settings = get_settings()

        if is_complex:
            return settings.reasoning_model

        if agent_role:
            role_key = agent_role.lower()
            tier = cls.ROLE_DEFAULTS.get(role_key, ModelTier.BALANCED)
            if tier == ModelTier.REASONING:
                return settings.reasoning_model
            elif tier == ModelTier.FAST:
                return settings.fast_model
            else:
                return settings.default_model

        return settings.default_model
