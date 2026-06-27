"""
LLM Service - Multi-provider LLM abstraction
Supports Claude, GPT, Gemini, Grok, Ollama, DeepSeek, Mistral, OpenRouter
"""
from typing import Optional, List
from config.settings import settings
import anthropic
import asyncio


class LLMService:
    """Multi-provider LLM service"""

    def __init__(self):
        self.default_provider = settings.llm.default_provider
        self.models = settings.llm.models

    async def generate_tests(
        self,
        provider: str,
        model: str,
        survived_mutant: dict,
        language: str,
    ) -> Optional[str]:
        """Generate tests for survived mutant using specified provider"""

        if provider == "ollama":
            return await self._generate_with_ollama(
                model, survived_mutant, language
            )
        elif provider == "claude":
            return await self._generate_with_claude(
                model, survived_mutant, language
            )
        elif provider == "gpt":
            return await self._generate_with_gpt(
                model, survived_mutant, language
            )
        else:
            # Default to Ollama
            return await self._generate_with_ollama(
                self.models.get("ollama"), survived_mutant, language
            )

    async def _generate_with_claude(
        self,
        model: str,
        survived_mutant: dict,
        language: str,
    ) -> Optional[str]:
        """Generate tests using Claude API"""
        try:
            api_key = settings.llm.claude_api_key
            if not api_key:
                return None

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""
            Generate a test case to kill the following survived mutation:

            File: {survived_mutant.get('file')}
            Language: {language}
            Mutation: {survived_mutant.get('description')}
            Original: {survived_mutant.get('original')}
            Mutated: {survived_mutant.get('mutated')}

            The test should:
            1. Pass with the original code
            2. Fail with the mutated code
            3. Be minimal and focused
            4. Follow {language} best practices

            Return ONLY the test code, no explanations.
            """

            message = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text

        except Exception as e:
            print(f"Error generating with Claude: {e}")
            return None

    async def _generate_with_gpt(
        self,
        model: str,
        survived_mutant: dict,
        language: str,
    ) -> Optional[str]:
        """Generate tests using GPT API"""
        # TODO: Implement OpenAI integration
        return None

    async def _generate_with_ollama(
        self,
        model: str,
        survived_mutant: dict,
        language: str,
    ) -> Optional[str]:
        """Generate tests using Ollama (local)"""
        try:
            import subprocess
            import json

            prompt = f"""
            Generate a test case to kill the following survived mutation:

            File: {survived_mutant.get('file')}
            Language: {language}
            Mutation: {survived_mutant.get('description')}
            Original: {survived_mutant.get('original')}
            Mutated: {survived_mutant.get('mutated')}

            The test should be minimal and focused.
            Return ONLY the test code.
            """

            result = subprocess.run(
                [
                    "ollama",
                    "run",
                    model,
                    prompt,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None

        except Exception as e:
            print(f"Error generating with Ollama: {e}")
            return None

    async def analyze_code(
        self,
        provider: str,
        model: str,
        code: str,
        language: str,
    ) -> Optional[dict]:
        """Analyze code and provide insights"""
        # TODO: Implement code analysis
        return None

    def get_available_models(self, provider: str) -> List[str]:
        """Get available models for provider"""
        # TODO: Fetch available models from provider
        return [self.models.get(provider, "default")]

    def validate_api_key(self, provider: str, api_key: str) -> bool:
        """Validate API key for provider"""
        if provider == "claude":
            try:
                client = anthropic.Anthropic(api_key=api_key)
                # Test with a simple call
                message = client.messages.create(
                    model="claude-opus-4-1",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "test"}],
                )
                return True
            except Exception:
                return False
        return False
