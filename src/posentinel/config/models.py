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
    enabled: bool = False
    auto_translate: bool = False
    provider: str = "anthropic"
    model: str = "claude-3-5-sonnet-20240620"
    base_url: str | None = None


@dataclass(frozen=True, slots=True)
class PoSentinelConfig:
    scan: ScanConfig
    project: ProjectConfig
    ai: AiConfig
