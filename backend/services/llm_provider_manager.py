"""
Smart LLM Provider Manager
Manages all 8 LLM providers with load balancing, failover, health checks, and cost tracking

Providers:
- Claude (Anthropic) - Most capable
- GPT-4o (OpenAI) - Fast, reliable
- Gemini (Google) - Advanced reasoning
- Grok (xAI) - Cutting-edge
- OpenRouter - 200+ models
- DeepSeek - Cost-effective
- Mistral - European, high-performance
- Ollama (Local) - 100% private, offline
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json


class LLMProvider(Enum):
    """All supported LLM providers"""
    CLAUDE = "claude"
    GPT4O = "gpt4o"
    GEMINI = "gemini"
    GROK = "grok"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    OLLAMA = "ollama"


class ProviderStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    provider: LLMProvider
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    enabled: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30
    retry_count: int = 3
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    priority: int = 5  # 1-10, higher is prioritized


@dataclass
class ProviderHealth:
    """Health status of a provider"""
    provider: LLMProvider
    status: ProviderStatus
    last_check: datetime
    response_time_ms: int
    error_count: int = 0
    success_count: int = 0
    uptime_percentage: float = 100.0
    last_error: Optional[str] = None


@dataclass
class ProviderUsage:
    """Usage statistics for a provider"""
    provider: LLMProvider
    request_count: int = 0
    token_count: int = 0
    error_count: int = 0
    total_cost: float = 0.0
    avg_response_time_ms: int = 0
    last_used: Optional[datetime] = None
    requests_today: int = 0


@dataclass
class CostReport:
    """Cost breakdown report"""
    period_start: datetime
    period_end: datetime
    total_cost: float = 0.0
    cost_by_provider: Dict[str, float] = field(default_factory=dict)
    request_count: int = 0
    token_count: int = 0
    requests_by_provider: Dict[str, int] = field(default_factory=dict)
    avg_cost_per_request: float = 0.0


class LLMProviderManager:
    """Manages all LLM providers with smart load balancing and failover"""

    def __init__(self):
        self.providers: Dict[LLMProvider, ProviderConfig] = {}
        self.health: Dict[LLMProvider, ProviderHealth] = {}
        self.usage: Dict[LLMProvider, ProviderUsage] = {}
        self.request_queue: List[Dict[str, Any]] = []
        self.fallback_chain: List[LLMProvider] = [
            LLMProvider.OLLAMA  # Local fallback
        ]

    def register_provider(self, config: ProviderConfig) -> None:
        """Register a provider configuration"""

        self.providers[config.provider] = config
        self.health[config.provider] = ProviderHealth(
            provider=config.provider,
            status=ProviderStatus.UNKNOWN,
            last_check=datetime.now(),
            response_time_ms=0
        )
        self.usage[config.provider] = ProviderUsage(
            provider=config.provider
        )

    def register_providers_from_config(self, config_dict: Dict[str, Any]) -> None:
        """Register multiple providers from configuration dict"""

        for provider_name, provider_config in config_dict.items():
            try:
                provider = LLMProvider[provider_name.upper()]
                config = ProviderConfig(
                    provider=provider,
                    api_key=provider_config.get('api_key'),
                    api_url=provider_config.get('api_url'),
                    enabled=provider_config.get('enabled', True),
                    max_tokens=provider_config.get('max_tokens', 4096),
                    temperature=provider_config.get('temperature', 0.7),
                    timeout=provider_config.get('timeout', 30),
                    retry_count=provider_config.get('retry_count', 3),
                    cost_per_1k_input=provider_config.get('cost_per_1k_input', 0.0),
                    cost_per_1k_output=provider_config.get('cost_per_1k_output', 0.0),
                    priority=provider_config.get('priority', 5)
                )
                self.register_provider(config)
            except KeyError:
                continue

    async def select_best_provider(
        self,
        task_type: str = "general",
        required_capabilities: List[str] = None,
        prefer_local: bool = False
    ) -> Optional[LLMProvider]:
        """
        Select best provider based on health, cost, and performance

        Args:
            task_type: Type of task (general, analysis, generation, etc.)
            required_capabilities: Required capabilities
            prefer_local: Prefer local Ollama if available

        Returns:
            Best provider or None if all down
        """

        enabled_providers = [
            p for p, c in self.providers.items()
            if c.enabled
        ]

        if not enabled_providers:
            return None

        # If prefer local and Ollama available, use it
        if prefer_local and LLMProvider.OLLAMA in enabled_providers:
            if self.health[LLMProvider.OLLAMA].status == ProviderStatus.HEALTHY:
                return LLMProvider.OLLAMA

        # Score providers
        scores = {}

        for provider in enabled_providers:
            score = self._calculate_provider_score(provider)
            scores[provider] = score

        # Return provider with highest score
        if scores:
            return max(scores, key=scores.get)

        return None

    async def generate_with_fallback(
        self,
        prompt: str,
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        task_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Generate response with automatic fallback to next provider

        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            task_type: Type of task for provider selection

        Returns:
            Response dict with provider info
        """

        # Select initial provider
        primary = await self.select_best_provider(task_type)

        if not primary:
            return {"error": "No providers available"}

        # Try primary provider
        result = await self._call_provider(
            provider=primary,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if result.get("success"):
            return result

        # Try fallback providers
        for fallback in self.fallback_chain:
            if fallback == primary:
                continue

            if not self.providers[fallback].enabled:
                continue

            result = await self._call_provider(
                provider=fallback,
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            if result.get("success"):
                return result

        return {"error": "All providers failed"}

    async def _call_provider(
        self,
        provider: LLMProvider,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Call a specific provider"""

        config = self.providers.get(provider)

        if not config:
            return {"success": False, "error": f"Provider {provider.value} not configured"}

        start_time = datetime.now()

        try:
            # Simulate provider call
            # In real implementation, would call actual provider API
            response = {
                "success": True,
                "provider": provider.value,
                "model": model,
                "response": f"Response from {provider.value}",
                "tokens_used": 100,
                "temperature": temperature
            }

            # Record usage
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            self._record_usage(provider, response, duration_ms)

            return response

        except Exception as e:
            self._record_error(provider, str(e))
            return {"success": False, "error": str(e)}

    async def check_provider_health(self, provider: LLMProvider) -> ProviderHealth:
        """Check health of a provider"""

        config = self.providers.get(provider)

        if not config:
            return ProviderHealth(
                provider=provider,
                status=ProviderStatus.UNKNOWN,
                last_check=datetime.now(),
                response_time_ms=0
            )

        start_time = datetime.now()

        try:
            # Simple health check: short API call
            # In real implementation, would call provider's health endpoint
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)

            health = ProviderHealth(
                provider=provider,
                status=ProviderStatus.HEALTHY,
                last_check=datetime.now(),
                response_time_ms=response_time
            )

            self.health[provider] = health
            return health

        except Exception as e:
            health = ProviderHealth(
                provider=provider,
                status=ProviderStatus.UNHEALTHY,
                last_check=datetime.now(),
                response_time_ms=0,
                last_error=str(e)
            )

            self.health[provider] = health
            return health

    async def check_all_health(self) -> Dict[LLMProvider, ProviderHealth]:
        """Check health of all providers"""

        tasks = [
            self.check_provider_health(provider)
            for provider in self.providers.keys()
        ]

        results = await asyncio.gather(*tasks)

        return {h.provider: h for h in results}

    def _calculate_provider_score(self, provider: LLMProvider) -> float:
        """Calculate score for provider selection"""

        config = self.providers[provider]
        health = self.health.get(provider)

        # Start with priority
        score = config.priority * 10

        # Health status
        if not health:
            score -= 50
        elif health.status == ProviderStatus.HEALTHY:
            score += 100
        elif health.status == ProviderStatus.DEGRADED:
            score += 50
        else:
            score -= 100

        # Response time (lower is better)
        if health and health.response_time_ms > 0:
            score -= health.response_time_ms / 100

        # Cost (lower is better)
        score -= (config.cost_per_1k_input + config.cost_per_1k_output) * 10

        return score

    def _record_usage(
        self,
        provider: LLMProvider,
        response: Dict[str, Any],
        duration_ms: int
    ) -> None:
        """Record usage statistics"""

        usage = self.usage[provider]
        tokens = response.get("tokens_used", 0)

        usage.request_count += 1
        usage.requests_today += 1
        usage.token_count += tokens
        usage.last_used = datetime.now()

        # Calculate cost
        config = self.providers[provider]
        input_cost = (tokens / 1000) * config.cost_per_1k_input
        usage.total_cost += input_cost

        # Update response time average
        usage.avg_response_time_ms = (
            (usage.avg_response_time_ms * (usage.request_count - 1) + duration_ms) /
            usage.request_count
        )

    def _record_error(self, provider: LLMProvider, error: str) -> None:
        """Record error for provider"""

        usage = self.usage[provider]
        usage.error_count += 1

        health = self.health.get(provider)
        if health:
            health.error_count += 1
            health.last_error = error

    def get_usage_report(
        self,
        provider: Optional[LLMProvider] = None
    ) -> Dict[str, Any]:
        """Get usage report for provider(s)"""

        if provider:
            usage = self.usage[provider]
            return {
                "provider": provider.value,
                "request_count": usage.request_count,
                "token_count": usage.token_count,
                "error_count": usage.error_count,
                "total_cost": usage.total_cost,
                "avg_response_time_ms": usage.avg_response_time_ms
            }

        # All providers
        return {
            "providers": {
                p.value: {
                    "request_count": self.usage[p].request_count,
                    "token_count": self.usage[p].token_count,
                    "error_count": self.usage[p].error_count,
                    "total_cost": self.usage[p].total_cost,
                    "avg_response_time_ms": self.usage[p].avg_response_time_ms
                }
                for p in self.usage.keys()
            }
        }

    def get_cost_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CostReport:
        """Generate cost report"""

        if not start_date:
            start_date = datetime.now() - timedelta(days=30)

        if not end_date:
            end_date = datetime.now()

        total_cost = 0.0
        total_requests = 0
        total_tokens = 0
        cost_by_provider = {}
        requests_by_provider = {}

        for provider, usage in self.usage.items():
            cost_by_provider[provider.value] = usage.total_cost
            requests_by_provider[provider.value] = usage.request_count

            total_cost += usage.total_cost
            total_requests += usage.request_count
            total_tokens += usage.token_count

        avg_cost = total_cost / total_requests if total_requests > 0 else 0

        return CostReport(
            period_start=start_date,
            period_end=end_date,
            total_cost=total_cost,
            cost_by_provider=cost_by_provider,
            request_count=total_requests,
            token_count=total_tokens,
            requests_by_provider=requests_by_provider,
            avg_cost_per_request=avg_cost
        )

    def get_health_report(self) -> Dict[str, Any]:
        """Get health report for all providers"""

        return {
            "timestamp": datetime.now().isoformat(),
            "providers": {
                h.provider.value: {
                    "status": h.status.value,
                    "response_time_ms": h.response_time_ms,
                    "uptime_percentage": h.uptime_percentage,
                    "error_count": h.error_count,
                    "success_count": h.success_count,
                    "last_error": h.last_error
                }
                for h in self.health.values()
            }
        }

    def export_configuration(self) -> Dict[str, Any]:
        """Export provider configuration"""

        return {
            "providers": {
                p.value: {
                    "enabled": config.enabled,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "timeout": config.timeout,
                    "priority": config.priority,
                    "cost_per_1k_input": config.cost_per_1k_input,
                    "cost_per_1k_output": config.cost_per_1k_output
                }
                for p, config in self.providers.items()
            },
            "fallback_chain": [p.value for p in self.fallback_chain]
        }
