from unittest.mock import Mock

import anthropic

from posentinel.ai.client import TranslationSuggester
from posentinel.ai.models import TranslationSuggestion
from posentinel.models import Issue, Severity, TranslationEntry


def test_translation_suggester_suggest() -> None:
    mock_client = Mock(spec=anthropic.Anthropic)
    mock_response = Mock()
    mock_response.parsed_output = TranslationSuggestion(msgstr="Olá")
    mock_client.messages.parse.return_value = mock_response

    suggester = TranslationSuggester("fake-model", client=mock_client)
    entry = TranslationEntry(msgid="Hello", msgstr="")
    issue = Issue(code="PO001", message="Vazio", severity=Severity.ERROR, msgid="Hello", line=1)

    suggestion = suggester.suggest(entry, issue, "en", "pt_BR")
    assert suggestion.msgstr == "Olá"
    mock_client.messages.parse.assert_called_once()
