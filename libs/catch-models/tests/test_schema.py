"""Tests for the bundled Gold-model JSON Schema artifact."""

from __future__ import annotations

from jsonschema.validators import validator_for

from catch_models.schema import build_schema, render_schema, schema_file_path


def test_schema_bundle_references_both_gold_documents():
    schema = build_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["oneOf"] == [
        {"$ref": "#/$defs/GoldTeamSchedule"},
        {"$ref": "#/$defs/GoldUpcomingGames"},
    ]
    assert "GoldTeamSchedule" in schema["$defs"]
    assert "GoldUpcomingGames" in schema["$defs"]


def test_schema_bundle_is_valid_json_schema():
    schema = build_schema()

    validator_for(schema).check_schema(schema)


def test_committed_schema_json_matches_generated_bundle():
    assert schema_file_path().read_text(encoding="utf-8") == render_schema()
