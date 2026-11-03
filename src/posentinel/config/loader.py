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
    """Carrega posentinel.toml buscando no diretório ou subindo diretórios ancestrais."""

    def find_config(self, start_path: Path) -> Path | None:
        current = start_path.resolve()
        if current.is_file():
            current = current.parent

        for directory in (current, *current.parents):
            candidate = directory / "posentinel.toml"
            if candidate.is_file():
                return candidate
        return None

    def load(self, cwd: Path, config_file: Path | None = None) -> PoSentinelConfig:
        config_path: Path | None
        if config_file is not None and config_file.is_file():
            config_path = config_file.resolve()
        else:
            config_path = self.find_config(cwd)

        if config_path is None or not config_path.is_file():
            return PoSentinelConfig(scan=ScanConfig(), project=ProjectConfig(), ai=AiConfig())

        try:
            data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            # Fallback for invalid TOML
            data = {}

        scan_data = {**_defaults(ScanConfig), **data.get("scan", {})}
        if isinstance(scan_data.get("ignore_rules"), list):
            scan_data["ignore_rules"] = tuple(scan_data["ignore_rules"])

        raw_glossary = data.get("glossary", {})
        glossary: dict[str, tuple[str, ...]] = {}
        for term, target_val in raw_glossary.items():
            if isinstance(target_val, (list, tuple)):
                glossary[term] = tuple(str(x) for x in target_val)
            else:
                glossary[term] = (str(target_val),)

        project_data = {**_defaults(ProjectConfig), **data.get("project", {})}
        project_data["glossary"] = glossary

        return PoSentinelConfig(
            scan=ScanConfig(**scan_data),
            project=ProjectConfig(**project_data),
            ai=AiConfig(**{**_defaults(AiConfig), **data.get("ai", {})}),
        )
