"""Motor de regras e regras de validação do PoSentinel."""

from posentinel.rules.base import BaseRule
from posentinel.rules.engine import RulesEngine
from posentinel.rules.fuzzy import FuzzyTranslationRule
from posentinel.rules.glossary import GlossaryRule
from posentinel.rules.odoo import OdooFormatRule
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.punctuation import PunctuationSpacingRule
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule

__all__ = [
    "BaseRule",
    "EmptyTranslationRule",
    "ExtraPlaceholderRule",
    "FuzzyTranslationRule",
    "GlossaryRule",
    "InvalidMarkupRule",
    "InvalidPlaceholderRule",
    "MissingPlaceholderRule",
    "OdooFormatRule",
    "PunctuationSpacingRule",
    "RulesEngine",
]
