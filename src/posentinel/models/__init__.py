"""Modelos de domínio imutáveis do PoSentinel."""

from posentinel.models.change import TranslationChange
from posentinel.models.entry import OdooMetadata, Severity, TranslationEntry
from posentinel.models.issue import Issue
from posentinel.models.result import ScanSummary

__all__ = [
    "Issue",
    "OdooMetadata",
    "ScanSummary",
    "Severity",
    "TranslationChange",
    "TranslationEntry",
]
