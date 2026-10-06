import anthropic

from posentinel.ai.models import TranslationSuggestion
from posentinel.ai.prompts import build_fix_prompt, build_generate_prompt
from posentinel.models import Issue, TranslationEntry


class TranslationSuggester:
    """Encapsula o SDK anthropic. Único ponto de contato com a API Claude no projeto."""

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
        """Uma chamada à API por entrada problemática — nunca em lote."""
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
        return response.parsed_output
