# feat: Define Gold layer Pydantic models for UI-ready JSON views

## What do you want to build?

Create Pydantic models in `libs/catch-models` that define the exact shape of the
Gold layer JSON files consumed by the catch-app frontend. These are the public
API contract of the entire pipeline. Two view models are needed:

1. **`GoldTeamSchedule`** — the full schedule for a single team (30 files:
   `gold/team_{teamId}.json`)
2. **`GoldUpcomingGames`** — a consolidated view of upcoming and recently
   completed games across all teams (`gold/upcoming_games.json`)

These models must be lean, containing only the fields the frontend needs. No
raw API artifacts or internal pipeline metadata should leak into Gold.

## Acceptance Criteria

- [ ] `catch_models/gold.py` contains a `GoldGameSummary` model with: `game_pk`, `date`, `status`, `home_team`, `away_team`, `score` (nullable), `condensed_game_url` (nullable)
- [ ] `GoldTeamSchedule` model wraps a list of `GoldGameSummary` with `team_id`, `team_name`, `team_abbreviation`, `season_year`, and `last_updated`
- [ ] `GoldUpcomingGames` model wraps a list of `GoldGameSummary` filtered to a rolling window (e.g., yesterday through 7 days out) with `last_updated`
- [ ] Team identity is represented as a lightweight `GoldTeamInfo` sub-model (id, name, abbreviation, league, division)
- [ ] `GoldGameSummary` includes `boxscore_summary` as an optional nested model (R/H/E, pitcher names) — present only for completed games
- [ ] All Gold models are JSON-serializable and produce clean output via `.model_dump(mode="json")`
- [ ] Unit tests validate Gold model construction from Silver model data (transformation contract test)
- [ ] All tests pass via `poetry run pytest` in `libs/catch-models`

## Implementation Notes

**⚡ PWA Performance Fanatic notes:**

- Gold JSON must be as small as possible. Use short field names where clarity
  is not sacrificed. Exclude any field the frontend does not currently need
  (YAGNI).
- `GoldGameSummary` should include pre-formatted display strings where it
  saves the frontend work (e.g., `"score_display": "5-3"` alongside raw run
  counts).

**⚾ Baseball Edge-Case Hunter notes:**

- Doubleheader handling: both games of a doubleheader should appear in the
  schedule with distinct `game_pk` values. Include a `game_number` field (1
  or 2) so the frontend can display "Game 1" / "Game 2" labels.
- Postponed games should appear with a clear status string. The frontend
  needs to distinguish Final, Postponed, Scheduled, and In Progress.
- Games without a condensed game video: `condensed_game_url` is `null`. The
  frontend should handle this gracefully (hide the button).

**🤑 FinOps Miser notes:**

- The 30 `team_{teamId}.json` files and one `upcoming_games.json` will be
  served via CloudFront. Keep total payload under 500 KB per file to minimize
  data transfer costs.
- Consider whether the `upcoming_games.json` window should be configurable.
  A 7-day window keeps the file small.

**📝 ADR Consideration:**

- This ticket's models will be used for JSON Schema generation (ticket 02-05).
  Ensure `model_json_schema()` produces a self-contained, $ref-free schema
  suitable for cross-repo consumption. If Pydantic's default schema output is
  not clean enough, document the decision to post-process it in an ADR.
