Title: feat: Implement JSON Schema generation from Gold Pydantic models

## What do you want to build?

Add a build step to `libs/catch-models` that generates a standard JSON Schema
file from the Gold layer Pydantic models. This schema file is the bridge between
the catch-data (Python) and catch-app (TypeScript) repositories — it enables
type-safe frontend development without a monorepo.

The generated schema will be committed to the repo (or produced as a CI
artifact) and used by the cross-repo sync workflow (Epic 7) to keep the frontend
types aligned with the backend data contract.

## Acceptance Criteria

- [ ] A `generate-schema` script/command in `libs/catch-models` produces a `schema.json` file containing the JSON Schema for `GoldTeamSchedule` and `GoldUpcomingGames`
- [ ] The generated schema is a single self-contained file with no external `$ref` references
- [ ] The schema includes `title` and `description` annotations from the Pydantic model docstrings
- [ ] Running the script is idempotent — regenerating produces identical output if models haven't changed
- [ ] A CI check verifies the committed `schema.json` is up-to-date with the current models (no drift)
- [ ] The schema validates against the JSON Schema Draft 2020-12 (or latest Pydantic-supported draft) spec
- [ ] Unit tests confirm the schema round-trips: Gold model → JSON Schema → validate Gold JSON output
- [ ] All tests pass via `poetry run pytest` in `libs/catch-models`

## Implementation Notes

Pydantic v2's `model_json_schema()` generates JSON Schema natively. However, it
may use `$defs` for nested models. If the catch-app's
`json-schema-to-typescript` tool struggles with `$defs`, post-process the schema
to inline definitions using a library like `jsonschema` or a custom script.

**Implementation approach:**

1. Add a Click command or standalone script:
   `catch_models/scripts/generate_schema.py`
2. Use `model_json_schema(GoldTeamSchedule)` and
   `model_json_schema(GoldUpcomingGames)` to produce schemas
3. Combine into a single file with a top-level `definitions` or `$defs` block
4. Write to `libs/catch-models/schema.json`

**🧪 QA notes:**

- The CI drift check should be a simple `diff` between the committed
  `schema.json` and a freshly generated one. If they differ, fail the build
  with a message to regenerate.
- Add a test that generates Gold model instances, dumps them to JSON, and
  validates that JSON against the generated schema using `jsonschema.validate`.

**📝 ADR Consideration:**

- This implements the Schema-Driven Development pattern from the PRD (Section
  5). Consider proposing an ADR that formally documents this cross-repo schema
  strategy, including the decision to use Pydantic as the SSOT and JSON Schema
  as the interchange format.

**🤑 FinOps Miser notes:**

- Schema generation runs in CI only — no runtime cost. The schema file itself
  is tiny (a few KB) and has zero serving cost.
