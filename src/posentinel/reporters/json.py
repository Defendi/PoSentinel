"""Serialização estruturada dos resultados de scan em JSON para pipelines de CI/CD."""

import json

from posentinel.models import Issue, ScanSummary


class JsonReporter:
    """Serializa os resultados do scan em um payload JSON estruturado."""

    def report(self, summaries: list[ScanSummary]) -> str:
        payload = {"results": [self._summary_to_dict(summary) for summary in summaries]}
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _summary_to_dict(self, summary: ScanSummary) -> dict[str, object]:
        return {
            "file_path": summary.file_path,
            "locale": summary.locale,
            "total_entries": summary.total_entries,
            "errors_count": summary.errors_count,
            "warnings_count": summary.warnings_count,
            "infos_count": summary.infos_count,
            "issues": [self._issue_to_dict(issue) for issue in summary.issues],
        }

    def _issue_to_dict(self, issue: Issue) -> dict[str, object]:
        return {
            "code": issue.code,
            "message": issue.message,
            "severity": issue.severity.value,
            "line": issue.line,
            "msgid": issue.msgid,
            "odoo_context": issue.odoo_context,
            "suggestion": issue.suggestion,
        }
