import re
from collections import Counter

from posentinel.models.entry import Severity, TranslationEntry
from posentinel.models.issue import Issue
from posentinel.rules.base import BaseRule


class InvalidMarkupRule(BaseRule):
    """PO005: Preservação de tags e estrutura básica de HTML/XML."""

    code = "PO005"
    description = "Tags HTML/XML omitidas, corrompidas ou desbalanceadas"
    default_severity = Severity.WARNING

    _TAG_PATTERN = re.compile(r"<\/?([a-zA-Z0-9]+)[^>]*>")

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not entry.msgstr.strip():
            return []

        orig_tags = [m.group(1).lower() for m in self._TAG_PATTERN.finditer(entry.msgid)]
        trans_tags = [m.group(1).lower() for m in self._TAG_PATTERN.finditer(entry.msgstr)]

        if not orig_tags:
            return []

        orig_counter = Counter(orig_tags)
        trans_counter = Counter(trans_tags)

        issues: list[Issue] = []
        for tag, count in orig_counter.items():
            t_count = trans_counter.get(tag, 0)
            if t_count < count:
                issues.append(
                    Issue(
                        code=self.code,
                        message=f"Tag HTML/XML <{tag}> do original foi omitida ou quebrada na tradução",
                        severity=self.default_severity,
                        line=entry.line,
                        msgid=entry.msgid,
                        entry=entry,
                        odoo_context=entry.odoo_metadata.module,
                    )
                )

        return issues
