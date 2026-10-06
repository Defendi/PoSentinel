from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanConfig:
    target: str = "."
    format: str = "console"
    fail_on: str = "error"


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    source_language: str = "en"
    target_language: str = "pt_BR"


@dataclass(frozen=True, slots=True)
class AiConfig:
    enabled: bool = True
    auto_translate: bool = False
    model: str = "claude-opus-5"


@dataclass(frozen=True, slots=True)
class PoSentinelConfig:
    scan: ScanConfig
    project: ProjectConfig
    ai: AiConfig
