import abc
import os

import anthropic
import openai
from posentinel.ai.models import TranslationSuggestion
from posentinel.ai.prompts import build_fix_prompt, build_generate_prompt
from posentinel.models import Issue, TranslationEntry


class BaseSuggester(abc.ABC):
    @abc.abstractmethod
    def suggest(
        self,
        entry: TranslationEntry,
        issue: Issue,
        source_language: str,
        target_language: str,
    ) -> TranslationSuggestion:
        pass


class AnthropicSuggester(BaseSuggester):
    """Suggester específico para API oficial da Anthropic (usa Claude)."""

    def __init__(self, model: str, client: anthropic.Anthropic | None = None) -> None:
        self._model = model
        self._client = client or anthropic.Anthropic()

    def suggest(
        self,
        entry: TranslationEntry,
        issue: Issue,
        source_language: str,
        target_language: str,
    ) -> TranslationSuggestion:
        prompt = (
            build_generate_prompt(entry, source_language, target_language)
            if issue.code == "PO001"
            else build_fix_prompt(entry, issue, source_language, target_language)
        )
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            output_format=TranslationSuggestion,
        )
        assert response.parsed_output is not None
        return response.parsed_output


class OpenAISuggester(BaseSuggester):
    """Suggester agnóstico que atende qualquer endpoint compatível com OpenAI (OpenRouter, Ollama, Groq, DeepSeek)."""

    def __init__(
        self, model: str, client: openai.OpenAI | None = None, base_url: str | None = None
    ) -> None:
        self._model = model
        if client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            # Provedores locais como Ollama não exigem chave, mas a biblioteca openai exige uma string
            if not api_key and base_url and ("localhost" in base_url or "127.0.0.1" in base_url):
                api_key = "dummy"

            self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        else:
            self._client = client

    def suggest(
        self,
        entry: TranslationEntry,
        issue: Issue,
        source_language: str,
        target_language: str,
    ) -> TranslationSuggestion:
        prompt = (
            build_generate_prompt(entry, source_language, target_language)
            if issue.code == "PO001"
            else build_fix_prompt(entry, issue, source_language, target_language)
        )

        # Usa Structured Outputs da OpenAI API
        response = self._client.beta.chat.completions.parse(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format=TranslationSuggestion,
        )
        assert response.choices[0].message.parsed is not None
        return response.choices[0].message.parsed


def TranslationSuggester(
    model: str,
    provider: str = "anthropic",
    base_url: str | None = None,
    client: anthropic.Anthropic | openai.OpenAI | None = None,
) -> BaseSuggester:
    """Factory que retorna o suggester apropriado."""
    if provider == "openai":
        return OpenAISuggester(
            model=model,
            base_url=base_url,
            client=client if isinstance(client, openai.OpenAI) else None,
        )
    return AnthropicSuggester(
        model=model, client=client if isinstance(client, anthropic.Anthropic) else None
    )
