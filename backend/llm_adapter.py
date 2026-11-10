"""
llm_adapter.py
Unified async interface for Claude / GPT / Grok / Ollama (in-house).
Select at runtime — no restart needed.
"""
import os
import httpx
from abc import ABC, abstractmethod


class LLMProviderError(ValueError):  # ValueError keeps existing handlers working
    """A provider failure with a stable code the UI can act on.

    codes: quota_exhausted | rate_limited | missing_key
    """

    def __init__(self, provider: str, code: str, message: str):
        super().__init__(message)
        self.provider = provider
        self.code = code


GEMINI_MESSAGES = {
    "quota_exhausted": "Gemini quota exhausted. Check your Google AI Studio usage and billing, or choose another configured provider.",
    "rate_limited": "Gemini rate limit reached. Please wait before retrying.",
    "missing_key": "Gemini API key is not configured.",
}


def classify_gemini_429(body: str, headers) -> str:
    """Quota exhaustion vs temporary rate limiting for an HTTP 429 from Gemini.

    Order matters. Google sends RetryInfo even for billing quota errors, so a retry
    hint alone does not make an error temporary. A per-minute limit is temporary.
    A quota or billing message means the quota is exhausted.
    """
    text = (body or "").lower()
    header_names = {str(k).lower() for k in (headers or {}).keys()}
    # Billing/quota wording first: quota details can carry ids such as "...PerMinute"
    # even for an exhausted quota, so the per-minute check must not run first.
    if "exceeded your current quota" in text or "billing" in text:
        return "quota_exhausted"
    if any(p in text for p in ("per minute", "perminute", "per-minute", "requests per")):
        return "rate_limited"
    if "quotafailure" in text:
        return "quota_exhausted"
    if "retrydelay" in text or "retryinfo" in text or "retry-after" in header_names:
        return "rate_limited"
    if "quota" in text:
        return "quota_exhausted"
    return "rate_limited"


def ollama_status(host: str = "http://localhost:11434", timeout: float = 3.0) -> dict:
    """Whether Ollama is running and the configured model is installed. Never raises."""
    try:
        r = httpx.get(f"{host}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        return {"available": False, "reason": "Ollama is not running"}
    model = create_adapter("ollama").model
    wanted = {model} if ":" in model else {model, model + ":latest"}
    if any(n in wanted for n in names):
        return {"available": True, "model": model}
    return {"available": False, "reason": f"model '{model}' is not installed"}


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
        # Key resolution: explicit argument (VS Code setting) first, then the
        # environment (populated from backend/.env at startup). Never logged.
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
        print(f"[GeminiAdapter.__init__] API key {'present' if self.api_key else 'MISSING'}", file=sys.stderr, flush=True)
        # Default: gemini-3.5-flash (verified available to current keys; 2.0/2.5 flash are retired)
        # Users can select gemini-3.5-flash if available, but defaults to stable model
        self.model = model or "gemini-3.5-flash"
        print(f"[GeminiAdapter.__init__] Model: {self.model}", file=sys.stderr, flush=True)

    @property
    def name(self) -> str:
        return "gemini"

    async def call_async(self, prompt: str, max_tokens: int = 500) -> str:
        import sys
        if not self.api_key:
            raise LLMProviderError("gemini", "missing_key", GEMINI_MESSAGES["missing_key"])

        async with httpx.AsyncClient(timeout=30) as client:
            # Try v1beta endpoint first, then v1 if that fails
            for api_version in ["v1beta", "v1"]:
                endpoint = f"https://generativelanguage.googleapis.com/{api_version}/models/{self.model}:generateContent"
                print(f"[GeminiAdapter.call_async] Trying {api_version} endpoint: {endpoint}", file=sys.stderr, flush=True)

                try:
                    # Key goes in a header, never in the URL: URLs end up in
                    # exception text, logs and the UI.
                    r = await client.post(
                        endpoint,
                        headers={"x-goog-api-key": self.api_key},
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"maxOutputTokens": max_tokens},
                        },
                    )
                    if r.status_code == 429:
                        # Not retried: retrying a quota error only wastes requests.
                        code = classify_gemini_429(r.text, r.headers)
                        print(f"[GeminiAdapter.call_async] HTTP 429 classified as {code}", file=sys.stderr, flush=True)
                        raise LLMProviderError("gemini", code, GEMINI_MESSAGES[code])
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
                except LLMProviderError:
                    raise
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
