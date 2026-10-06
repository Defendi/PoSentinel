from collections.abc import Callable

from posentinel.ai.client import BaseSuggester
from posentinel.ai.models import TranslationSuggestion
from posentinel.models import Issue, ScanSummary, TranslationChange, TranslationEntry

ConfirmFn = Callable[[TranslationEntry, Issue, TranslationSuggestion], bool]


class TranslationAssistant:
    def __init__(
        self,
        suggester: BaseSuggester,
        auto_translate: bool,
        confirm: ConfirmFn,
    ) -> None:
        self._suggester = suggester
        self._auto_translate = auto_translate
        self._confirm = confirm

    def process(
        self,
        summary: ScanSummary,
        entries_by_msgid: dict[str, TranslationEntry],
        source_language: str,
        target_language: str,
    ) -> list[TranslationChange]:
        """Para cada Issue elegível do summary, gera sugestão e decide aplicar."""
        changes = []
        for issue in summary.issues:
            if issue.code == "SYS001" or issue.msgid is None:
                continue
            entry = entries_by_msgid.get(issue.msgid)
            if entry is None:
                continue

            suggestion = self._suggester.suggest(entry, issue, source_language, target_language)
            applied = self._auto_translate or self._confirm(entry, issue, suggestion)
            changes.append(
                TranslationChange(
                    msgid=entry.msgid,
                    old_msgstr=entry.msgstr,
                    new_msgstr=suggestion.msgstr,
                    issue_code=issue.code,
                    applied=applied,
                )
            )
        return changes
