from pathlib import Path

from posentinel.config.loader import ConfigLoader
from posentinel.config.models import PoSentinelConfig


def test_config_loader_missing_file(tmp_path: Path) -> None:
    loader = ConfigLoader()
    config = loader.load(tmp_path)

    assert isinstance(config, PoSentinelConfig)
    assert config.scan.target == "."
    assert config.ai.enabled is True
    assert config.project.source_language == "en"


def test_config_loader_partial_override(tmp_path: Path) -> None:
    config_file = tmp_path / "posentinel.toml"
    config_file.write_text(
        '[scan]\ntarget = "./src"\n[ai]\nmodel = "custom-model"\n',
        encoding="utf-8",
    )

    loader = ConfigLoader()
    config = loader.load(tmp_path)

    assert config.scan.target == "./src"
    assert config.ai.model == "custom-model"
    assert config.scan.format == "console"
    assert config.ai.enabled is True
    assert config.project.source_language == "en"


def test_config_loader_invalid_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "posentinel.toml"
    config_file.write_text("invalid [ toml content", encoding="utf-8")

    loader = ConfigLoader()
    config = loader.load(tmp_path)

    assert config.scan.target == "."
    assert config.ai.enabled is True
