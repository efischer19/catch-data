Title: feat: GitHub Action to auto-generate JSON Schema on merge to main

## What do you want to build?

Create a GitHub Actions workflow in catch-data that automatically regenerates
the `schema.json` file from Gold Pydantic models whenever changes to
`libs/catch-models/` are merged to the `main` branch. This ensures the schema
is always synchronized with the Python data models and serves as the first step
in the cross-repo schema sync pipeline.

## Acceptance Criteria

- [ ] A new workflow `.github/workflows/schema-generate.yml` triggers on pushes to `main` that modify files in `libs/catch-models/`
- [ ] The workflow runs the schema generation script from `libs/catch-models`
- [ ] The workflow compares the generated `schema.json` with the committed version
- [ ] If the schema has changed, the workflow commits and pushes the updated `schema.json` to `main` (using a bot commit)
- [ ] If the schema has changed, the workflow triggers the cross-repo PR workflow (ticket 07-02)
- [ ] If the schema is unchanged, the workflow exits cleanly with a success log
- [ ] The workflow uses the project's standard Python/Poetry setup action
- [ ] The workflow has minimal permissions: `contents: write` (for the commit) and no access to other repositories
- [ ] The workflow passes CI validation (YAML lint, dry-run)

## Implementation Notes

**😴 Lazy Maintainer notes:**

- This workflow eliminates the manual step of "remember to regenerate the
  schema after changing models." It's fully automatic.
- The bot commit to `main` should use a recognizable author (e.g.,
  `github-actions[bot]`) and a conventional commit message (e.g.,
  `chore: regenerate schema.json from Gold models`).
- The workflow should be idempotent: if triggered multiple times for the same
  model state, it produces the same schema and makes no unnecessary commits.

**🔧 Data Pipeline Janitor notes:**

- Use `paths` filter in the workflow trigger to avoid running on unrelated
  changes: `paths: ['libs/catch-models/**']`.
- The schema file should be committed to a well-known location:
  `libs/catch-models/schema.json`. This location is referenced by the
  cross-repo workflow and the CI drift check.

**🧪 QA notes:**

- The CI workflow (ci.yml) should already include a schema drift check (from
  ticket 02-05) that fails if `schema.json` is out of date. This workflow is
  the automated fix for that check.
- Add a test in the workflow that validates the generated schema against the
  JSON Schema meta-schema (i.e., the schema itself is valid JSON Schema).

**🤑 FinOps Miser notes:**

- GitHub Actions minutes: this workflow runs only when models change (rare
  outside of active development). Expected runtime: <1 minute. Negligible cost.

Reference ADR-014 (CI/CD Strategy) for workflow conventions.
