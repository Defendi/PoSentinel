from pydantic import BaseModel


class TranslationSuggestion(BaseModel):
    msgstr: str
    reasoning: str | None = None
