"""
llm_adapter.py
Unified async interface for Claude / GPT / Grok / Ollama (in-house).
Select at runtime — no restart needed.
"""
import os
import httpx
from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    @abstractmethod
    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


# ── Claude (Anthropic) ─────────────────────────────────────────────────────

class ClaudeAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-5"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    @property
    def name(self): return "claude"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        if not self.api_key:
            raise ValueError("Anthropic Claude API key not configured. Set amil.anthropicApiKey in VS Code settings.")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]


# ── GPT (OpenAI) ───────────────────────────────────────────────────────────

class GPTAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model

    @property
    def name(self): return "gpt"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Set amil.openaiApiKey in VS Code settings.")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


# ── Grok (xAI) ─────────────────────────────────────────────────────────────

class GrokAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str = None, model: str = "grok-3"):
        self.api_key = api_key or os.getenv("XAI_API_KEY", "")
        self.model = model

    @property
    def name(self): return "grok"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        if not self.api_key:
            raise ValueError("xAI Grok API key not configured. Set amil.xaiApiKey in VS Code settings.")
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]


# ── Ollama (in-house, fully offline) ──────────────────────────────────────

class OllamaAdapter(BaseLLMAdapter):
    def __init__(self, model: str = "llama3", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host

    @property
    def name(self): return "inhouse"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        # Local Ollama on CPU can be VERY slow. Generous timeouts since it's the user's machine.
        # Timeout strategy:
        # - Small tokens (<=200): 120s (fast local models)
        # - Medium tokens (200-500): 180s (moderate speed)
        # - Large tokens (500-1000): 300s (slower generation)
        # - Very large (>1000): 600s (full test suites on CPU)
        if max_tokens <= 200:
            timeout = 120
        elif max_tokens <= 500:
            timeout = 180
        elif max_tokens <= 1000:
            timeout = 300
        else:
            timeout = 600  # 10 minutes for full suites

        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
            )
            r.raise_for_status()
            return r.json()["response"]


# ── No LLM (pure in-house mode) ────────────────────────────────────────────

class NoLLMAdapter(BaseLLMAdapter):
    @property
    def name(self): return "none"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        return '{"equivalent": false, "confidence": "low", "reason": "No LLM configured", "counterexample_input": null}'


# ── Provider Registry (NEW ARCHITECTURE - Non-disruptive) ──────────────────

PROVIDER_REGISTRY = {
    "claude": {
        "adapter_class": "claude",
        "label": "Claude",
        "endpoint": "https://api.anthropic.com/v1/messages",
        "auth_type": "x-api-key",
        "model_default": "claude-sonnet-4-5",
    },
    "gpt": {
        "adapter_class": "openai_compatible",
        "label": "GPT-4o",
        "endpoint": "https://api.openai.com/v1/chat/completions",
        "auth_type": "bearer",
        "model_default": "gpt-4o",
    },
    "openrouter": {
        "adapter_class": "openai_compatible",
        "label": "OpenRouter",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "auth_type": "bearer",
        "model_default": "auto",
    },
    "deepseek": {
        "adapter_class": "openai_compatible",
        "label": "DeepSeek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "auth_type": "bearer",
        "model_default": "deepseek-chat",
    },
    "mistral": {
        "adapter_class": "openai_compatible",
        "label": "Mistral",
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "auth_type": "bearer",
        "model_default": "mistral-large-latest",
    },
    "gemini": {
        "adapter_class": "gemini",
        "label": "Gemini",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth_type": "x-goog-api-key",
        "model_default": "gemini-1.5-pro",
    },
    "grok": {
        "adapter_class": "grok",
        "label": "Grok",
        "endpoint": "https://api.x.ai/v1/chat/completions",
        "auth_type": "bearer",
        "model_default": "grok-3",
    },
    "ollama": {
        "adapter_class": "ollama",
        "label": "Ollama",
        "endpoint": "http://localhost:11434/api/generate",
        "auth_type": "none",
        "model_default": "llama3",
    },
}


class OpenAICompatibleAdapter(BaseLLMAdapter):
    """Handles OpenAI-compatible providers: GPT, OpenRouter, DeepSeek, Mistral"""

    def __init__(self, provider: str, api_key: str = None, model: str = None):
        self.provider = provider
        config = PROVIDER_REGISTRY.get(provider, {})
        self.endpoint = config.get("endpoint", "https://api.openai.com/v1/chat/completions")
        self.model = model or config.get("model_default", "gpt-4o")
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY", "")

    @property
    def name(self) -> str:
        return self.provider

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        import sys
        if not self.api_key:
            raise ValueError(
                f"{self.provider.upper()} API key not configured. "
                f"Set the {self.provider.upper()}_API_KEY environment variable or VS Code setting."
            )
        async with httpx.AsyncClient(timeout=30) as client:
            print(f"[OpenAICompatibleAdapter] Provider: {self.provider}, Model: {self.model}, Endpoint: {self.endpoint}", file=sys.stderr, flush=True)
            try:
                r = await client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self.model,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                r.raise_for_status()
                response = r.json()
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[OpenAICompatibleAdapter] Error: {str(e)[:200]}", file=sys.stderr, flush=True)
                try:
                    print(f"[OpenAICompatibleAdapter] Response: {r.text[:300]}", file=sys.stderr, flush=True)
                except:
                    pass
                raise


class GeminiAdapter(BaseLLMAdapter):
    """Handles Google Gemini API"""

    def __init__(self, api_key: str = None, model: str = None):
        import sys
        print(f"[GeminiAdapter.__init__] Called with api_key={api_key if api_key else 'NONE'}", file=sys.stderr, flush=True)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        print(f"[GeminiAdapter.__init__] Final api_key set to: {self.api_key if self.api_key else 'NONE'}", file=sys.stderr, flush=True)
        # Use stable model: gemini-2.0-flash (reliable, less overloaded than newest)
        # Users can select gemini-3.5-flash if available, but defaults to stable model
        self.model = model or "gemini-2.0-flash"
        print(f"[GeminiAdapter.__init__] Model: {self.model}", file=sys.stderr, flush=True)

    @property
    def name(self) -> str:
        return "gemini"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        import sys
        print(f"[GeminiAdapter.call_async] Checking api_key: {self.api_key if self.api_key else 'NONE'}", file=sys.stderr, flush=True)
        if not self.api_key:
            raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY environment variable.")

        async with httpx.AsyncClient(timeout=30) as client:
            # Try v1beta endpoint first, then v1 if that fails
            for api_version in ["v1beta", "v1"]:
                endpoint = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:generateContent"
                print(f"[GeminiAdapter.call_async] Trying {api_version} endpoint: {endpoint}", file=sys.stderr, flush=True)

                try:
                    r = await client.post(
                        endpoint,
                        params={"key": self.api_key},
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": max_tokens},
                        },
                    )
                    if r.status_code == 404 and api_version == "v1beta":
                        print(f"[GeminiAdapter.call_async] v1beta not available, trying v1", file=sys.stderr, flush=True)
                        continue

                    r.raise_for_status()
                    response = r.json()
                    print(f"[GeminiAdapter.call_async] Response keys: {list(response.keys())}", file=sys.stderr, flush=True)
                    print(f"[GeminiAdapter.call_async] Full response: {str(response)[:500]}", file=sys.stderr, flush=True)

                    # Extract text from response
                    candidates = response.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            print(f"[GeminiAdapter.call_async] Extracted text length: {len(text)}", file=sys.stderr, flush=True)
                            print(f"[GeminiAdapter.call_async] Extracted text: {text[:200]}", file=sys.stderr, flush=True)
                            return text

                    raise Exception(f"Invalid response format: {list(response.keys())}")
                except Exception as e:
                    error_msg = str(e)
                    try:
                        # Try to get more details from the response
                        resp_text = r.text if 'r' in locals() else ""
                        print(f"[GeminiAdapter.call_async] Response: {resp_text[:300]}", file=sys.stderr, flush=True)
                    except:
                        pass

                    if api_version == "v1":
                        print(f"[GeminiAdapter.call_async] Final error: {error_msg}", file=sys.stderr, flush=True)
                        raise
                    continue


# ── Factory ────────────────────────────────────────────────────────────────

def create_adapter(provider: str, **kwargs) -> BaseLLMAdapter:
    """
    provider: "claude" | "gpt" | "grok" | "ollama" | "gemini" | "openrouter" | "deepseek" | "mistral" | "none"

    Uses new provider registry architecture while maintaining backward compatibility.
    Pass api_key and model as kwargs if needed.
    """
    provider_lower = provider.lower()

    # Handle new architecture providers
    if provider_lower in PROVIDER_REGISTRY:
        config = PROVIDER_REGISTRY[provider_lower]
        adapter_type = config.get("adapter_class")

        if adapter_type == "claude":
            return ClaudeAdapter(api_key=kwargs.get("api_key"), model=kwargs.get("model"))
        elif adapter_type == "openai_compatible":
            return OpenAICompatibleAdapter(
                provider=provider_lower,
                api_key=kwargs.get("api_key"),
                model=kwargs.get("model"),
            )
        elif adapter_type == "gemini":
            return GeminiAdapter(api_key=kwargs.get("api_key"), model=kwargs.get("model"))
        elif adapter_type == "grok":
            return GrokAdapter(api_key=kwargs.get("api_key"), model=kwargs.get("model"))
        elif adapter_type == "ollama":
            return OllamaAdapter(model=kwargs.get("model", "llama3"))

    # Handle legacy names
    legacy_map = {
        "inhouse": OllamaAdapter,
        "none": NoLLMAdapter,
    }
    if provider_lower in legacy_map:
        return legacy_map[provider_lower](**kwargs)

    # Unknown provider
    valid = list(PROVIDER_REGISTRY.keys()) + list(legacy_map.keys())
    raise ValueError(
        f"Unknown LLM provider: {provider}. "
        f"Choose from: {', '.join(sorted(valid))}"
    )
