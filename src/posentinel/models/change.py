from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationChange:
    msgid: str
    old_msgstr: str
    new_msgstr: str
    issue_code: str
    applied: bool
