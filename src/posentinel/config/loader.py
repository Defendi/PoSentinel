import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):  # noqa: UP036
    import tomllib
else:
    # Fallback for local testing if running < 3.11
    import tomli as tomllib

from posentinel.config.models import AiConfig, PoSentinelConfig, ProjectConfig, ScanConfig


def _defaults(cls: type) -> dict[str, Any]:
    return {f.name: f.default for f in fields(cls)}


class ConfigLoader:
    """Carrega posentinel.toml do diretório atual; retorna defaults se ausente."""

    def load(self, cwd: Path) -> PoSentinelConfig:
        config_path = cwd / "posentinel.toml"
        if not config_path.is_file():
            return PoSentinelConfig(scan=ScanConfig(), project=ProjectConfig(), ai=AiConfig())

        try:
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            # Fallback for invalid TOML
            data = {}

        return PoSentinelConfig(
            scan=ScanConfig(**{**_defaults(ScanConfig), **data.get("scan", {})}),
            project=ProjectConfig(**{**_defaults(ProjectConfig), **data.get("project", {})}),
            ai=AiConfig(**{**_defaults(AiConfig), **data.get("ai", {})}),
        )
