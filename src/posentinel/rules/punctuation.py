"""Regra PO010: conformidade de pontuação, espaços iniciais/finais e quebras de linha."""

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_PUNCTUATION = (".", ":", "?", "!", ";", ",")


class PunctuationSpacingRule(BaseRule):
    """Detecta divergências de pontuação, quebras de linha e espaçamento inicial/final."""

    code = "PO010"
    description = "Divergência de pontuação ou espaçamento inicial/final"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        orig = entry.msgid
        if not orig:
            return []

        issues: list[Issue] = []
        for translation in entry.all_translations:
            if not translation:
                continue

            # 1. Espaço inicial
            orig_leading_space = orig.startswith(" ") or orig.startswith("\t")
            trans_leading_space = translation.startswith(" ") or translation.startswith("\t")
            if orig_leading_space != trans_leading_space:
                desc = "ausente" if orig_leading_space else "extra"
                issues.append(
                    self._issue(
                        entry,
                        f"Espaço em branco inicial {desc} na tradução.",
                        translation=translation,
                    )
                )

            # 2. Espaço final
            orig_trailing_space = orig.endswith(" ") or orig.endswith("\t")
            trans_trailing_space = translation.endswith(" ") or translation.endswith("\t")
            if orig_trailing_space != trans_trailing_space:
                desc = "ausente" if orig_trailing_space else "extra"
                issues.append(
                    self._issue(
                        entry,
                        f"Espaço em branco final {desc} na tradução.",
                        translation=translation,
                    )
                )

            # 3. Quebra de linha final (\n)
            orig_trailing_newline = orig.endswith("\n")
            trans_trailing_newline = translation.endswith("\n")
            if orig_trailing_newline != trans_trailing_newline:
                desc = "ausente" if orig_trailing_newline else "extra"
                issues.append(
                    self._issue(
                        entry,
                        f"Quebra de linha final (\\n) {desc} na tradução.",
                        translation=translation,
                    )
                )

            # 4. Pontuação terminal (. : ? ! ; ,)
            orig_stripped = orig.rstrip(" \t\n\r")
            trans_stripped = translation.rstrip(" \t\n\r")
            if orig_stripped and trans_stripped:
                orig_punct = orig_stripped[-1] if orig_stripped[-1] in _PUNCTUATION else None
                trans_punct = trans_stripped[-1] if trans_stripped[-1] in _PUNCTUATION else None

                if orig_punct != trans_punct:
                    if orig_punct is not None and trans_punct is None:
                        msg = f"Pontuação final '{orig_punct}' ausente na tradução."
                    elif orig_punct is None and trans_punct is not None:
                        msg = (
                            f"Pontuação final '{trans_punct}' adicionada indevidamente na tradução."
                        )
                    else:
                        msg = (
                            f"Pontuação final diverge: esperado '{orig_punct}', "
                            f"obtido '{trans_punct}'."
                        )
                    issues.append(
                        self._issue(
                            entry,
                            msg,
                            suggestion=orig_punct,
                            translation=translation,
                        )
                    )

        return issues
