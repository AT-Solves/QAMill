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
        # Local model on CPU can be slow for large generations (e.g. full test
        # suites). Generous timeout since it's the user's own machine.
        async with httpx.AsyncClient(timeout=300) as client:
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


# ── Factory ────────────────────────────────────────────────────────────────

def create_adapter(provider: str, **kwargs) -> BaseLLMAdapter:
    """
    provider: "claude" | "gpt" | "grok" | "inhouse" | "none"
    Pass api_key and model as kwargs if needed.
    """
    adapters = {
        "claude":  ClaudeAdapter,
        "gpt":     GPTAdapter,
        "grok":    GrokAdapter,
        "inhouse": OllamaAdapter,
        "none":    NoLLMAdapter,
    }
    cls = adapters.get(provider.lower())
    if cls is None:
        raise ValueError(f"Unknown LLM provider: {provider}. "
                         f"Choose from: {list(adapters.keys())}")
    return cls(**kwargs)
