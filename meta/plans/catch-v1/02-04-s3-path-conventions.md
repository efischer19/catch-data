Title: feat: Define S3 path conventions for MLB catch-data pipeline

## What do you want to build?

Implement the `MedallionPaths` class (or equivalent) in `libs/catch-models`
that generates consistent, type-safe S3 key prefixes for all three pipeline
layers. This replaces the template's generic path conventions with
catch-data-specific paths matching the PRD specification.

The key layout:

```text
s3://{bucket}/
├── bronze/schedule_{year}.json
├── bronze/boxscore_{gamePk}.json
├── bronze/content_{gamePk}.json
├── silver/master_schedule_{year}.json
├── gold/team_{teamId}.json
└── gold/upcoming_games.json
```

## Acceptance Criteria

- [ ] `catch_models/s3_paths.py` contains a `CatchPaths` class (or similar) with methods to generate every S3 key used in the pipeline
- [ ] `bronze_schedule_key(year: int) -> str` returns `"bronze/schedule_{year}.json"`
- [ ] `bronze_boxscore_key(game_pk: int) -> str` returns `"bronze/boxscore_{game_pk}.json"`
- [ ] `bronze_content_key(game_pk: int) -> str` returns `"bronze/content_{game_pk}.json"`
- [ ] `silver_master_schedule_key(year: int) -> str` returns `"silver/master_schedule_{year}.json"`
- [ ] `gold_team_key(team_id: int) -> str` returns `"gold/team_{team_id}.json"`
- [ ] `gold_upcoming_games_key() -> str` returns `"gold/upcoming_games.json"`
- [ ] All methods are tested with unit tests
- [ ] Path generation is deterministic and produces no leading slashes or double slashes

## Implementation Notes

Follow the existing `MedallionPaths` pattern from `libs/example-data/` but
customize for MLB-specific entities. The class should be a simple namespace —
no state, no S3 client dependency. It generates string keys only.

**🔧 Data Pipeline Janitor notes:**

- Key names use underscores, not hyphens, for consistency with the PRD.
- The Bronze layer keys use flat naming (`bronze/schedule_2025.json`) rather
  than date-partitioned directories. This is intentional per the PRD — the
  schedule file is overwritten nightly with the full season, not appended.
- Boxscore and content keys use `gamePk` as the unique identifier. A single
  `gamePk` should always map to exactly one boxscore and one content key.

**😴 Lazy Maintainer notes:**

- Centralizing all path logic here means pipeline apps never construct S3 keys
  manually. If the key scheme ever changes, only this file needs updating.

Reference ADR-018 for the Medallion Architecture S3 key layout conventions.
