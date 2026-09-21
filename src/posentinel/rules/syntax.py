"""Regra PO005: preservação e balanceamento de tags HTML/XML na tradução."""

import re
from dataclasses import dataclass

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_TAG_PATTERN = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*?(/?)>")


@dataclass(frozen=True, slots=True)
class _Tag:
    name: str
    kind: str  # "open" | "close" | "self"


def _extract_tags(text: str) -> list[_Tag]:
    tags = []
    for closing, name, self_closing in _TAG_PATTERN.findall(text):
        if closing == "/":
            kind = "close"
        elif self_closing == "/":
            kind = "self"
        else:
            kind = "open"
        tags.append(_Tag(name=name.lower(), kind=kind))
    return tags


def _is_balanced(tags: list[_Tag]) -> bool:
    stack: list[str] = []
    for tag in tags:
        if tag.kind == "open":
            stack.append(tag.name)
        elif tag.kind == "close":
            if not stack or stack[-1] != tag.name:
                return False
            stack.pop()
    return not stack


class InvalidMarkupRule(BaseRule):
    code = "PO005"
    description = "Tags HTML/XML omitidas ou desequilibradas na tradução"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        original_names = {tag.name for tag in _extract_tags(entry.msgid)}
        if not original_names:
            return []

        issues = []
        for translation in entry.all_translations:
            translated_tags = _extract_tags(translation)
            translated_names = {tag.name for tag in translated_tags}

            missing = original_names - translated_names
            if missing:
                tags_text = ", ".join(f"<{name}>" for name in sorted(missing))
                issues.append(
                    self._issue(entry, f"Tag(s) HTML/XML ausente(s) na tradução: {tags_text}")
                )

            if not _is_balanced(translated_tags):
                issues.append(self._issue(entry, "Tags HTML/XML desequilibradas na tradução"))

        return issues
