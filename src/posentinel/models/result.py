from dataclasses import dataclass, field

from posentinel.models.entry import Severity
from posentinel.models.issue import Issue


@dataclass(slots=True)
class ScanSummary:
    file_path: str
    locale: str | None = None
    total_entries: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.ERROR)

    @property
    def warnings_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.WARNING)

    @property
    def infos_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.INFO)

    @property
    def has_errors(self) -> bool:
        return self.errors_count > 0
