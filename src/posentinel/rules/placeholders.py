"""Regras PO002, PO003 e PO004: integridade de placeholders na tradução.

Reconhece três estilos de placeholder: printf posicional (`%s`, `%d`, ...), printf
nomeado (`%(name)s`) e campos `str.format` (`{name}`, `{0}`, `{name!r}`). A
comparação entre original e tradução é feita por contagem exata de tokens canônicos
(multiset/Counter), garantindo detecção de omissões, repetições indevidas e discrepâncias.
"""

import re
from collections import Counter
from dataclasses import dataclass

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_CONVERSIONS = "diouxXeEfFgGcrsa"

# Formato printf completo: %[(nome)][flags][largura][.precisão]conversão
# Exemplos: %s, %d, %.2f, %10.3f, %(nome)s, %(target).2f, %-5d, %+08.2f
_PRINTF_SPEC = rf"[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlL]?[{_CONVERSIONS}]"

_PLACEHOLDER_PATTERN = re.compile(
    r"%%"
    rf"|%\((?P<pname>[^)]+)\)(?P<pconv>{_PRINTF_SPEC})"
    rf"|%(?P<posconv>{_PRINTF_SPEC})"
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


def _diff_multiset(
    original: list[_Placeholder], translated: list[_Placeholder]
) -> tuple[Counter[str], Counter[str], list[tuple[str, str]]]:
    """Compara placeholders do original e da tradução via multiset (Counter).

    Retorna:
      - missing_counts: Counter de tokens ausentes (ou com menos ocorrências que o original)
      - extra_counts: Counter de tokens extras (ou com mais ocorrências que o original)
      - substitutions: pares de (token_traduzido_erroneamente, token_esperado)
    """
    orig_counter = Counter(p.token for p in original)
    trans_counter = Counter(p.token for p in translated)

    orig_by_token = {p.token: p for p in original}
    trans_by_token = {p.token: p for p in translated}

    missing_counts = orig_counter - trans_counter
    extra_counts = trans_counter - orig_counter

    substitutions: list[tuple[str, str]] = []

    # Detectar substituições de variáveis nomeadas (PO003)
    for missing_token in sorted(missing_counts.keys()):
        missing_ph = orig_by_token[missing_token]
        if missing_ph.name is None:
            continue

        while missing_counts[missing_token] > 0:
            candidates = sorted(
                token
                for token, count in extra_counts.items()
                if count > 0 and trans_by_token[token].shape == missing_ph.shape
            )
            if not candidates:
                break

            chosen = candidates[0]
            substitutions.append((chosen, missing_token))
            missing_counts[missing_token] -= 1
            extra_counts[chosen] -= 1

    missing_counts += Counter()  # remove zeros/negativos
    extra_counts += Counter()

    return missing_counts, extra_counts, substitutions


class MissingPlaceholderRule(BaseRule):
    code = "PO002"
    description = "Placeholder do original ausente na tradução"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        issues = []
        for source_text, translation in entry.translation_pairs:
            original = _extract_placeholders(source_text)
            if not original:
                continue

            translated = _extract_placeholders(translation)
            missing, _extra, _substitutions = _diff_multiset(original, translated)
            if missing:
                # Se houver repetição de falta, formatar de forma clara
                tokens_desc = []
                for token, count in sorted(missing.items()):
                    if count > 1:
                        tokens_desc.append(f"{token} ({count}x)")
                    else:
                        tokens_desc.append(token)
                tokens = ", ".join(tokens_desc)
                issues.append(
                    self._issue(
                        entry,
                        f"Placeholder(s) ausente(s) na tradução: {tokens}",
                        translation=translation,
                    )
                )
        return issues


class InvalidPlaceholderRule(BaseRule):
    code = "PO003"
    description = "Variável nomeada traduzida por engano ou caractere '%' solto"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        issues = []
        for source_text, translation in entry.translation_pairs:
            original = _extract_placeholders(source_text)

            # 1. Checagem de '%' solto/inválido que gera ValueError ao formatar em Python.
            # Compara a contagem de '%' órfãos entre o original e a tradução.
            # Reporta apenas quando a tradução introduz '%' solto extra que não existia no original
            # e a entrada possui a flag 'python-format' ou placeholders printf.
            orig_cleaned = _PLACEHOLDER_PATTERN.sub("", source_text)
            trans_cleaned = _PLACEHOLDER_PATTERN.sub("", translation)
            orig_loose_percent = orig_cleaned.count("%")
            trans_loose_percent = trans_cleaned.count("%")

            has_printf_template = entry.is_python_format or any(
                p.token.startswith("%") for p in original
            )

            if has_printf_template and trans_loose_percent > orig_loose_percent:
                diff_count = trans_loose_percent - orig_loose_percent
                desc = f" ({diff_count}x)" if diff_count > 1 else ""
                issues.append(
                    self._issue(
                        entry,
                        f"Caractere '%' solto extra na tradução{desc} "
                        "(use '%%' para escapar o sinal de porcentagem no Python).",
                        severity=Severity.WARNING,
                        translation=translation,
                    )
                )

            if not original:
                continue

            translated = _extract_placeholders(translation)
            _missing, _extra, substitutions = _diff_multiset(original, translated)
            for wrong_token, expected_token in substitutions:
                message = (
                    f"Placeholder '{expected_token}' foi traduzido "
                    f"incorretamente para '{wrong_token}'"
                )
                issues.append(
                    self._issue(entry, message, suggestion=expected_token, translation=translation)
                )
        return issues


class ExtraPlaceholderRule(BaseRule):
    code = "PO004"
    description = "Tradução contém mais placeholders do que o original"
    default_severity = Severity.ERROR

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        issues = []
        for source_text, translation in entry.translation_pairs:
            translated = _extract_placeholders(translation)
            if not translated:
                continue

            # Checar se misturou printf posicional (%s) com printf nomeado (%(x)s)
            has_pos_printf = any(
                p.token.startswith("%") and not p.token.startswith("%(") for p in translated
            )
            has_named_printf = any(p.token.startswith("%(") for p in translated)
            if has_pos_printf and has_named_printf:
                issues.append(
                    self._issue(
                        entry,
                        "Tradução mistura formatação printf posicional (%s) com nomeada (%(x)s), "
                        "o que causa erro em tempo de execução no Python.",
                        translation=translation,
                    )
                )

            original = _extract_placeholders(source_text)
            _missing, extra, _substitutions = _diff_multiset(original, translated)
            if extra:
                tokens_desc = []
                for token, count in sorted(extra.items()):
                    if count > 1:
                        tokens_desc.append(f"{token} ({count}x)")
                    else:
                        tokens_desc.append(token)
                tokens = ", ".join(tokens_desc)
                message = f"Placeholder(s) extra(s) na tradução, ausente(s) no original: {tokens}"
                issues.append(self._issue(entry, message, translation=translation))
        return issues
