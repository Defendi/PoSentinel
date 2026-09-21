from posentinel.rules.base import BaseRule
from posentinel.rules.engine import RulesEngine
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule


def get_default_rules() -> list[BaseRule]:
    return [
        EmptyTranslationRule(),
        MissingPlaceholderRule(),
        InvalidPlaceholderRule(),
        ExtraPlaceholderRule(),
        InvalidMarkupRule(),
    ]


__all__ = [
    "BaseRule",
    "RulesEngine",
    "EmptyTranslationRule",
    "MissingPlaceholderRule",
    "InvalidPlaceholderRule",
    "ExtraPlaceholderRule",
    "InvalidMarkupRule",
    "get_default_rules",
]
