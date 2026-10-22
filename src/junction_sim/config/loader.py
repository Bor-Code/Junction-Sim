import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from junction_sim.config.schema import ScenarioConfig
from junction_sim.exceptions import ConfigurationError


def load_scenario_from_dict(data: dict[str, Any]) -> ScenarioConfig:
    if not isinstance(data, dict):
        raise ConfigurationError("configuration root must be a dictionary")
    try:
        return ScenarioConfig.model_validate(data)
    except PydanticValidationError as exc:
        raise ConfigurationError(f"invalid scenario configuration: {exc}") from exc


def load_scenario_from_json(json_str: str) -> ScenarioConfig:
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"invalid JSON syntax: {exc}") from exc
    return load_scenario_from_dict(data)


def load_scenario_from_file(file_path: Path | str) -> ScenarioConfig:
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError) as exc:
        raise ConfigurationError(
            f"failed to read configuration file '{path}': {exc}"
        ) from exc
    return load_scenario_from_json(content)
