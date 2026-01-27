"""
Intelligent provider selection and routing logic.
Chooses the best AI provider based on task requirements, cost, and availability.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from hcode.providers.base import AIProvider, ModelType
from hcode.providers.anthropic_provider import AnthropicProvider
from hcode.providers.openai_provider import OpenAIProvider


class TaskComplexity(Enum):
    """Task complexity levels"""

    SIMPLE = "simple"  # Documentation, simple fixes
    MODERATE = "moderate"  # Standard implementation
    COMPLEX = "complex"  # Architecture, refactoring


class TaskType(Enum):
    """Types of coding tasks"""

    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    CODE_REVIEW = "reviewing"


@dataclass
class ProviderPreferences:
    """User preferences for provider selection"""

    primary_provider: str = "auto"  # "auto", "anthropic", "openai"
    fallback_enabled: bool = True
    cost_optimization: str = "balanced"  # "aggressive", "balanced", "quality"
    prefer_streaming: bool = True
    max_cost_per_request: float = 1.0  # USD


class ProviderSelector:
    """Selects optimal AI provider for tasks"""

    def __init__(
        self,
        anthropic_key: Optional[str] = None,
        openai_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        anthropic_model: Optional[str] = None,
        openai_model: Optional[str] = None,
        preferences: Optional[ProviderPreferences] = None,
    ):
        """
        Initialize provider selector.

        Args:
            anthropic_key: Anthropic API key
            openai_key: OpenAI API key
            openai_base_url: Optional custom base URL for OpenAI API
            anthropic_model: Specific Anthropic model name (overrides preferences)
            openai_model: Specific OpenAI model name (overrides preferences)
            preferences: User preferences
        """
        self.preferences = preferences or ProviderPreferences()
        self.providers: Dict[str, AIProvider] = {}
        self.openai_base_url = openai_base_url
        self.anthropic_model = anthropic_model
        self.openai_model = openai_model

        # Initialize available providers
        if anthropic_key:
            try:
                self.providers["anthropic"] = self._create_anthropic_provider(anthropic_key)
            except Exception as e:
                print(f"Warning: Could not initialize Anthropic provider: {e}")

        if openai_key:
            try:
                self.providers["openai"] = self._create_openai_provider(openai_key)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI provider: {e}")

        if not self.providers:
            raise ValueError("At least one AI provider must be available")

    def _create_anthropic_provider(self, api_key: str) -> AnthropicProvider:
        """Create Anthropic provider with appropriate model"""
        model = self.anthropic_model if self.anthropic_model else self._select_anthropic_model()
        return AnthropicProvider(api_key=api_key, model=model)

    def _create_openai_provider(self, api_key: str) -> OpenAIProvider:
        """Create OpenAI provider with appropriate model"""
        from hcode.config.prompts import get_generation_params

        model = self.openai_model if self.openai_model else self._select_openai_model()
        params = get_generation_params()

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            base_url=self.openai_base_url,
            max_tokens=params.max_tokens,
        )

    def _select_anthropic_model(self) -> str:
        """Select appropriate Anthropic model based on preferences"""
        if self.preferences.cost_optimization == "aggressive":
            return "claude-3-haiku-20240307"
        elif self.preferences.cost_optimization == "quality":
            return "claude-3-opus-20240229"
        else:  # balanced
            return "claude-3-5-sonnet-20241022"

    def _select_openai_model(self) -> str:
        """Select appropriate OpenAI model based on preferences"""
        if self.preferences.cost_optimization == "aggressive":
            return "gpt-4o-mini"
        elif self.preferences.cost_optimization == "quality":
            return "gpt-4-turbo"
        else:  # balanced
            return "gpt-4o"

    def select_provider(
        self,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        task_type: TaskType = TaskType.CODE_GENERATION,
        requires_vision: bool = False,
        requires_function_calling: bool = False,
        estimated_tokens: Optional[int] = None,
    ) -> AIProvider:
        """
        Select the best provider for a task.

        Args:
            complexity: Task complexity
            task_type: Type of task
            requires_vision: Whether vision capabilities are needed
            requires_function_calling: Whether function calling is needed
            estimated_tokens: Estimated token count

        Returns:
            Selected AI provider
        """
        # Honor user's primary provider preference if set
        if self.preferences.primary_provider != "auto":
            if self.preferences.primary_provider in self.providers:
                provider = self.providers[self.preferences.primary_provider]
                if self._is_provider_suitable(
                    provider, requires_vision, requires_function_calling, estimated_tokens
                ):
                    return provider

        # Intelligent selection based on task characteristics
        scores = {}

        for name, provider in self.providers.items():
            score = self._score_provider(
                provider,
                complexity,
                task_type,
                requires_vision,
                requires_function_calling,
                estimated_tokens,
            )
            scores[name] = score

        # Select provider with highest score
        best_provider_name = max(scores, key=scores.get)
        return self.providers[best_provider_name]

    def _score_provider(
        self,
        provider: AIProvider,
        complexity: TaskComplexity,
        task_type: TaskType,
        requires_vision: bool,
        requires_function_calling: bool,
        estimated_tokens: Optional[int],
    ) -> float:
        """
        Score a provider for a task (higher is better).

        Args:
            provider: Provider to score
            complexity: Task complexity
            task_type: Task type
            requires_vision: Vision required
            requires_function_calling: Function calling required
            estimated_tokens: Estimated tokens

        Returns:
            Score (0-100)
        """
        score = 50.0  # Base score

        # Check hard requirements
        if requires_vision and not provider.supports_vision():
            return 0.0
        if requires_function_calling and not provider.supports_function_calling():
            return 0.0

        # Context window check
        if estimated_tokens and estimated_tokens > provider.get_context_window():
            return 0.0

        # Provider strengths
        provider_name = provider.get_provider_name().lower()

        if provider_name == "anthropic":
            # Claude strengths
            if complexity == TaskComplexity.COMPLEX:
                score += 15
            if task_type in [TaskType.ARCHITECTURE, TaskType.REFACTORING]:
                score += 10
            if estimated_tokens and estimated_tokens > 50000:
                score += 10  # Better for large contexts
        elif provider_name == "openai":
            # GPT strengths
            if requires_function_calling:
                score += 15  # OpenAI has more mature function calling
            if task_type == TaskType.CODE_GENERATION:
                score += 5

        # Cost optimization
        if self.preferences.cost_optimization == "aggressive":
            # Favor cheaper models
            if provider_name == "anthropic" and "haiku" in provider.model:
                score += 20
            elif provider_name == "openai" and "mini" in provider.model:
                score += 20
        elif self.preferences.cost_optimization == "quality":
            # Favor better models
            if provider_name == "anthropic" and "opus" in provider.model:
                score += 10
            elif provider_name == "openai" and "gpt-4" in provider.model:
                score += 10

        return score

    def _is_provider_suitable(
        self,
        provider: AIProvider,
        requires_vision: bool,
        requires_function_calling: bool,
        estimated_tokens: Optional[int],
    ) -> bool:
        """Check if provider meets basic requirements"""
        if requires_vision and not provider.supports_vision():
            return False
        if requires_function_calling and not provider.supports_function_calling():
            return False
        if estimated_tokens and estimated_tokens > provider.get_context_window():
            return False
        return True

    def get_fallback_provider(self, current_provider: AIProvider) -> Optional[AIProvider]:
        """
        Get fallback provider when current one fails.

        Args:
            current_provider: Current provider that failed

        Returns:
            Fallback provider or None
        """
        if not self.preferences.fallback_enabled:
            return None

        current_name = current_provider.get_provider_name().lower()

        # Try to find a different provider
        for name, provider in self.providers.items():
            if name != current_name:
                return provider

        return None

    def switch_provider(self, from_provider: str, to_provider: str) -> bool:
        """
        Switch from one provider to another.

        Args:
            from_provider: Current provider name
            to_provider: Target provider name

        Returns:
            True if switch successful
        """
        if to_provider in self.providers:
            return True
        return False

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())

    def get_provider_by_name(self, name: str) -> Optional[AIProvider]:
        """Get provider by name"""
        return self.providers.get(name.lower())

    def update_model(self, provider_name: str, model: str):
        """
        Update the model for a specific provider.

        Args:
            provider_name: Provider to update
            model: New model name
        """
        if provider_name in self.providers:
            self.providers[provider_name].model = model
