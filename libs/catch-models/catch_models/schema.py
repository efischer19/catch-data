"""Generate the bundled JSON Schema for Gold-layer public models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from catch_models.gold import GoldTeamSchedule, GoldUpcomingGames

_JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_TITLE = "Catch Data Gold Schemas"
_SCHEMA_DESCRIPTION = "Bundled JSON Schemas for Gold-layer public models."
_TOP_LEVEL_MODELS = (
    (GoldTeamSchedule, "validation"),
    (GoldUpcomingGames, "validation"),
)


def schema_file_path() -> Path:
    """Return the committed schema.json location for catch-models."""

    return Path(__file__).resolve().parents[1] / "schema.json"


def build_schema() -> dict[str, object]:
    """Build a bundled JSON Schema for the public Gold-layer models."""

    top_level_refs, schema = models_json_schema(
        _TOP_LEVEL_MODELS,
        title=_SCHEMA_TITLE,
        description=_SCHEMA_DESCRIPTION,
    )
    return {
        "$schema": _JSON_SCHEMA_DRAFT,
        "title": _SCHEMA_TITLE,
        "description": _SCHEMA_DESCRIPTION,
        "oneOf": [
            top_level_refs[(GoldTeamSchedule, "validation")],
            top_level_refs[(GoldUpcomingGames, "validation")],
        ],
        "$defs": schema["$defs"],
    }


def render_schema() -> str:
    """Render the bundled schema as stable, pretty-printed JSON."""

    return json.dumps(build_schema(), indent=2, sort_keys=True) + "\n"


def write_schema_file(path: Path | None = None) -> Path:
    """Write the bundled schema to disk and return the destination path."""

    output_path = path or schema_file_path()
    output_path.write_text(render_schema(), encoding="utf-8")
    return output_path


def main() -> int:
    """CLI entrypoint for regenerating schema.json."""

    output_path = write_schema_file()
    print(f"✅ Wrote Gold model schema to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
