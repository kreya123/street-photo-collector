from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> Any:
    """Load JSON-compatible YAML without dependencies, or full YAML when PyYAML exists."""
    config_path = Path(path)
    text = config_path.read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ModuleNotFoundError:
        return json.loads(text)


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    data = load_config(path)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list of sources")
    return data


def load_genres(path: str | Path) -> dict[str, Any]:
    data = load_config(path)
    if not isinstance(data, dict) or "genres" not in data:
        raise ValueError(f"{path} must contain a mapping with a 'genres' key")
    return data


def load_article_types(path: str | Path) -> dict[str, Any]:
    data = load_config(path)
    if not isinstance(data, dict) or "types" not in data or "score_rules" not in data:
        raise ValueError(f"{path} must contain 'types' and 'score_rules' keys")
    return data
