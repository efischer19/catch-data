# feat: Define Silver layer Pydantic models for cleaned game data

## What do you want to build?

Create Pydantic models in `libs/catch-models` that represent the Silver layer's
cleaned, flattened, and joined game data. The Silver layer produces a single
`master_schedule_{year}.json` file that joins schedule, boxscore, and content
data into a unified game object. These models define that output contract.

Key model: a `SilverGame` object that contains:

- Game identity (gamePk, date, teams, venue)
- Game state (status, score, inning)
- Boxscore summary (R/H/E, winning/losing/save pitchers)
- Highlight video URL (condensed game .mp4, if available)

And a `SilverMasterSchedule` container that holds a list of `SilverGame` objects
for an entire season.

## Acceptance Criteria

- [ ] `catch_models/silver.py` contains a `SilverGame` Pydantic v2 model with all fields listed above
- [ ] `SilverGame` includes typed fields for home/away team IDs, team names, and abbreviations
- [ ] `SilverGame` includes an optional `condensed_game_url` field (nullable for games without highlights)
- [ ] `SilverGame` includes boxscore summary fields: runs, hits, errors per team, plus winning/losing/save pitcher names
- [ ] `SilverMasterSchedule` wraps a list of `SilverGame` with a `year` field and metadata (last_updated timestamp)
- [ ] Timestamps are standardized to UTC ISO 8601 format
- [ ] Unit tests validate model construction from realistic data, including edge cases
- [ ] All tests pass via `poetry run pytest` in `libs/catch-models`

## Implementation Notes

The Silver model is the single source of truth (SSOT) for the pipeline — it
must be rich enough that Gold layer views can be sliced from it without going
back to Bronze.

**⚾ Baseball Edge-Case Hunter notes:**

- Doubleheader games: `SilverGame` needs a `game_number` field (1 or 2) and
  a `doubleheader_type` field (traditional "Y" or split "S").
- Postponed/cancelled games: include a `status_detail` field with values like
  "Final", "Postponed", "Suspended", "Cancelled". Boxscore fields should be
  nullable for games that never started.
- Games in progress: the nightly batch should not process games that haven't
  reached "Final" status, but the model should accept "In Progress" status
  gracefully.
- Extra-inning games: the `innings` count may exceed 9. Do not hardcode
  a 9-inning assumption.
- Spring Training and All-Star games: include a `game_type` field to
  distinguish regular season ("R"), postseason, spring training ("S"), and
  All-Star ("A"). V1 focuses on regular season but the model should not
  break on other types.

**🔧 Data Pipeline Janitor notes:**

- The model should include a `source_updated_at` timestamp recording when the
  Bronze data was last refreshed, enabling staleness detection.
- Include a `data_completeness` enum or flag to indicate whether the game has
  full boxscore data, partial data, or no data yet.

Use `model_json_schema()` to verify the schema is clean and JSON-serializable,
as it will be used for cross-repo schema generation in Epic 7.
