"""Regras PO002, PO003 e PO004: integridade de placeholders na tradução.

Reconhece três estilos de placeholder: printf posicional (`%s`, `%d`, ...), printf
nomeado (`%(name)s`) e campos `str.format` (`{name}`, `{0}`, `{name!r}`). A
comparação entre original e tradução é feita por presença de token canônico (não por
contagem), o que mantém o MVP simples e determinístico.
"""

import re
from dataclasses import dataclass

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_CONVERSIONS = "diouxXeEfFgGcrsa"

_PLACEHOLDER_PATTERN = re.compile(
    r"%%"
    rf"|%\((?P<pname>[^)]+)\)(?P<pconv>[{_CONVERSIONS}])"
    rf"|%(?P<posconv>[{_CONVERSIONS}])"
    r"|\{(?P<field>[^{}]*)\}"
)


@dataclass(frozen=True, slots=True)
class _Placeholder:
    """Representação canônica de um placeholder extraído de uma string."""

    token: str
    shape: str
    name: str | None


def _format_field_name(content: str) -> str | None:
    name_part = content.split("!", 1)[0].split(":", 1)[0]
    if name_part and not name_part.isdigit():
        return name_part
    return None


def _extract_placeholders(text: str) -> list[_Placeholder]:
    placeholders: list[_Placeholder] = []
    for match in _PLACEHOLDER_PATTERN.finditer(text):
        if match.group() == "%%":
            continue

        if match.group("pname") is not None:
            name = match.group("pname")
            conv = match.group("pconv")
            placeholders.append(
                _Placeholder(token=f"%({name}){conv}", shape=f"%(*){conv}", name=name)
            )
        elif match.group("posconv") is not None:
            token = f"%{match.group('posconv')}"
            placeholders.append(_Placeholder(token=token, shape=token, name=None))
        else:
            content = match.group("field")
            name = _format_field_name(content)
            if name:
                placeholders.append(_Placeholder(token=f"{{{name}}}", shape="{*}", name=name))
            else:
                token = f"{{{content}}}"
                placeholders.append(_Placeholder(token=token, shape=token, name=None))
    return placeholders


def _diff(
    original: list[_Placeholder], translated: list[_Placeholder]
) -> tuple[set[str], set[str], list[tuple[str, str]]]:
    """Compara placeholders do original e da tradução.

    Retorna (tokens ausentes, tokens extras, pares de substituição) onde cada par de
    substituição é (token traduzido incorretamente, token esperado).
    """
    original_by_token = {p.token: p for p in original}
    translated_by_token = {p.token: p for p in translated}

    missing = set(original_by_token) - set(translated_by_token)
    extra = set(translated_by_token) - set(original_by_token)

    substitutions: list[tuple[str, str]] = []
    for missing_token in sorted(missing):
        missing_placeholder = original_by_token[missing_token]
        if missing_placeholder.name is None:
            continue

        candidates = sorted(
            token
            for token in extra
            if translated_by_token[token].shape == missing_placeholder.shape
        )
        if candidates:
            chosen = candidates[0]
            substitutions.append((chosen, missing_token))
            extra.discard(chosen)

    paired_missing = {expected for _wrong, expected in substitutions}
    missing -= paired_missing

    return missing, extra, substitutions


class MissingPlaceholderRule(BaseRule):
    code = "PO002"
    description = "Placeholder do original ausente na tradução"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        original = _extract_placeholders(entry.msgid)
        if not original:
            return []

        issues = []
        for translation in entry.all_translations:
            translated = _extract_placeholders(translation)
            missing, _extra, _substitutions = _diff(original, translated)
            if missing:
                tokens = ", ".join(sorted(missing))
                issues.append(
                    self._issue(entry, f"Placeholder(s) ausente(s) na tradução: {tokens}")
                )
        return issues


class InvalidPlaceholderRule(BaseRule):
    code = "PO003"
    description = "Variável nomeada traduzida por engano"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        original = _extract_placeholders(entry.msgid)
        if not original:
            return []

        issues = []
        for translation in entry.all_translations:
            translated = _extract_placeholders(translation)
            _missing, _extra, substitutions = _diff(original, translated)
            for wrong_token, expected_token in substitutions:
                message = (
                    f"Placeholder '{expected_token}' foi traduzido "
                    f"incorretamente para '{wrong_token}'"
                )
                issues.append(self._issue(entry, message, suggestion=expected_token))
        return issues


class ExtraPlaceholderRule(BaseRule):
    code = "PO004"
    description = "Tradução contém mais placeholders do que o original"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        original = _extract_placeholders(entry.msgid)

        issues = []
        for translation in entry.all_translations:
            translated = _extract_placeholders(translation)
            if not translated:
                continue
            _missing, extra, _substitutions = _diff(original, translated)
            if extra:
                tokens = ", ".join(sorted(extra))
                message = f"Placeholder(s) extra(s) na tradução, ausente(s) no original: {tokens}"
                issues.append(self._issue(entry, message))
        return issues
