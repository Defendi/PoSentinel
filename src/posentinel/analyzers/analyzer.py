"""Orquestrador de varredura: coordena PoParser e RulesEngine por arquivo/diretório."""

from pathlib import Path

from posentinel.models import ScanSummary
from posentinel.parser.po_parser import PoParser
from posentinel.rules.engine import RulesEngine


class TranslationAnalyzer:
    """Analisa um arquivo `.po` único ou varre recursivamente um diretório."""

    def __init__(self, parser: PoParser, engine: RulesEngine) -> None:
        self._parser = parser
        self._engine = engine

    def analyze_path(self, path: Path) -> list[ScanSummary]:
        if path.is_dir():
            return [self._analyze_file(po_file) for po_file in self._discover_po_files(path)]
        return [self._analyze_file(path)]

    def _discover_po_files(self, directory: Path) -> list[Path]:
        return sorted(directory.rglob("*.po"))

    def _analyze_file(self, path: Path) -> ScanSummary:
        parse_result = self._parser.parse_file(path)

        issues = list(parse_result.issues)
        for entry in parse_result.entries:
            issues.extend(self._engine.analyze(entry))

        return ScanSummary(
            file_path=str(path),
            locale=path.stem,
            total_entries=len(parse_result.entries),
            issues=issues,
        )
