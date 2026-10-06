from unittest.mock import Mock

from posentinel.ai.client import TranslationSuggester
from posentinel.ai.models import TranslationSuggestion
from posentinel.ai.orchestrator import TranslationAssistant
from posentinel.models import Issue, ScanSummary, Severity, TranslationEntry


def test_orchestrator_process() -> None:
    suggester = Mock(spec=TranslationSuggester)
    suggester.suggest.return_value = TranslationSuggestion(msgstr="Olá")

    assistant = TranslationAssistant(
        suggester, auto_translate=True, confirm=lambda _e, _i, _s: True
    )

    issue = Issue(code="PO001", message="Vazio", severity=Severity.ERROR, msgid="Hello", line=1)
    summary = ScanSummary(file_path="test.po", total_entries=1, issues=[issue])
    entries = {"Hello": TranslationEntry(msgid="Hello", msgstr="")}

    changes = assistant.process(summary, entries, "en", "pt_BR")
    assert len(changes) == 1
    assert changes[0].new_msgstr == "Olá"
    assert changes[0].applied is True
