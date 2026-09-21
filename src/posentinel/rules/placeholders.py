import re
from collections import Counter

from posentinel.models.entry import Severity, TranslationEntry
from posentinel.models.issue import Issue
from posentinel.rules.base import BaseRule


class PlaceholderExtractor:
    # Captura:
    # 1. %(name)s ou %(name)d
    # 2. %s, %d, %f, %.2f, etc.
    # 3. {name} ou {0}
    _PYTHON_PRINTF_NAMED = re.compile(r"%\([a-zA-Z0-9_]+\)[-# +0-9\.]*[diouxXeEfFgGcrs%]")
    _PYTHON_PRINTF_POS = re.compile(r"%(?:[-# +0-9\.]*)?[diouxXeEfFgGcrs]")
    _PYTHON_FORMAT_BRACES = re.compile(r"\{[a-zA-Z0-9_]*\}")

    @classmethod
    def extract_all(cls, text: str) -> list[str]:
        if not text:
            return []

        placeholders: list[str] = []
        # Extrair nomeados primeiro %(var)s
        named_matches = cls._PYTHON_PRINTF_NAMED.findall(text)
        placeholders.extend(named_matches)

        # Substituir os nomeados temporariamente para não duplicar com posicionais
        text_without_named = cls._PYTHON_PRINTF_NAMED.sub("", text)

        # Extrair posicionais %s, %d... evitando %%
        raw_pos = cls._PYTHON_PRINTF_POS.findall(text_without_named)
        pos_matches = [p for p in raw_pos if p != "%%"]
        placeholders.extend(pos_matches)

        # Extrair chaves {var} / {0}
        brace_matches = cls._PYTHON_FORMAT_BRACES.findall(text)
        placeholders.extend(brace_matches)

        return placeholders


class MissingPlaceholderRule(BaseRule):
    """PO002: Placeholder presente no original ausente na tradução."""

    code = "PO002"
    description = "Placeholder presente no original ausente na tradução"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not entry.msgstr.strip():
            return []

        orig_ph = PlaceholderExtractor.extract_all(entry.msgid)
        trans_ph = PlaceholderExtractor.extract_all(entry.msgstr)

        orig_counts = Counter(orig_ph)
        trans_counts = Counter(trans_ph)

        issues: list[Issue] = []
        for ph, count in orig_counts.items():
            trans_c = trans_counts.get(ph, 0)
            if trans_c < count:
                missing_diff = count - trans_c
                issues.append(
                    Issue(
                        code=self.code,
                        message=f"Placeholder '{ph}' ausente na tradução ({missing_diff} ocorrência(s) a menos)",
                        severity=self.default_severity,
                        line=entry.line,
                        msgid=entry.msgid,
                        entry=entry,
                        odoo_context=entry.odoo_metadata.module,
                    )
                )

        return issues


class InvalidPlaceholderRule(BaseRule):
    """PO003: Placeholder inválido ou inadvertidamente traduzido."""

    code = "PO003"
    description = "Placeholder nomeado traduzido ou corrompido"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not entry.msgstr.strip():
            return []

        orig_ph = set(PlaceholderExtractor.extract_all(entry.msgid))
        trans_ph = set(PlaceholderExtractor.extract_all(entry.msgstr))

        # Se existiam placeholders nomeados no original mas outros nomeados apareceram na tradução
        orig_named = {
            p for p in orig_ph if p.startswith("%(") or (p.startswith("{") and len(p) > 2)
        }
        trans_named = {
            p for p in trans_ph if p.startswith("%(") or (p.startswith("{") and len(p) > 2)
        }

        invalid_translated = trans_named - orig_named
        issues: list[Issue] = []
        for inv in invalid_translated:
            issues.append(
                Issue(
                    code=self.code,
                    message=f"Placeholder '{inv}' na tradução não existe no texto original (possível tradução indevida de variável)",
                    severity=self.default_severity,
                    line=entry.line,
                    msgid=entry.msgid,
                    entry=entry,
                    odoo_context=entry.odoo_metadata.module,
                )
            )

        return issues


class ExtraPlaceholderRule(BaseRule):
    """PO004: Placeholder extra na tradução inexistente no original."""

    code = "PO004"
    description = "Placeholder extra na tradução que não existe no original"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not entry.msgstr.strip():
            return []

        orig_ph = PlaceholderExtractor.extract_all(entry.msgid)
        trans_ph = PlaceholderExtractor.extract_all(entry.msgstr)

        orig_counts = Counter(orig_ph)
        trans_counts = Counter(trans_ph)

        issues: list[Issue] = []
        for ph, count in trans_counts.items():
            orig_c = orig_counts.get(ph, 0)
            if count > orig_c and not (ph.startswith("%(") or (ph.startswith("{") and len(ph) > 2)):
                extra_diff = count - orig_c
                issues.append(
                    Issue(
                        code=self.code,
                        message=f"Tradução contém placeholder extra '{ph}' ({extra_diff} a mais)",
                        severity=self.default_severity,
                        line=entry.line,
                        msgid=entry.msgid,
                        entry=entry,
                        odoo_context=entry.odoo_metadata.module,
                    )
                )

        return issues
