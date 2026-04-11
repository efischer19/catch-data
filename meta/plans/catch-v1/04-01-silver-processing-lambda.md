Title: feat: Implement Silver layer Lambda to clean and join game data

## What do you want to build?

Build the AWS Lambda function in `apps/catch-processing` that transforms Bronze
layer data into the Silver layer's `master_schedule_{year}.json`. This Lambda
reads the raw schedule, boxscore, and content files from Bronze, flattens the
MLB API's deeply nested JSON, standardizes timestamps, and joins boxscore
metadata and condensed game video URLs onto their respective game objects.

## Acceptance Criteria

- [ ] `app/main.py` contains a Lambda handler function that processes S3 event notifications
- [ ] The handler reads `bronze/schedule_{year}.json` and parses it using Bronze Pydantic models
- [ ] For each game in the schedule with status "Final", the handler reads the corresponding `bronze/boxscore_{gamePk}.json` and `bronze/content_{gamePk}.json`
- [ ] Boxscore data is flattened into `SilverGame` fields: R/H/E per team, winning/losing/save pitcher names
- [ ] Content data is parsed to extract the condensed game `.mp4` URL and attach it to the `SilverGame`
- [ ] All game timestamps are standardized to UTC ISO 8601 format
- [ ] The complete joined dataset is written to `silver/master_schedule_{year}.json` as a `SilverMasterSchedule` model
- [ ] Missing boxscore or content files (not yet ingested) result in a `SilverGame` with null optional fields, not an error
- [ ] The Lambda output is validated against the Silver Pydantic model before S3 write
- [ ] Unit tests cover: schedule parsing, boxscore joining, content joining, missing-data handling, timestamp normalization
- [ ] All tests pass via `poetry run pytest` in `apps/catch-processing`

## Implementation Notes

**🔧 Data Pipeline Janitor notes:**

- The Lambda reads all Bronze files for the year and produces a complete Silver
  file. This is a full rebuild, not an incremental update. This simplifies the
  logic at the cost of processing all games every night.
- Pydantic validation on the output guarantees the Silver file is always
  schema-compliant. If a single game fails validation, log the error and
  exclude that game from the output — do not fail the entire Lambda.
- The `last_updated` field on `SilverMasterSchedule` should be set to the
  Lambda execution time (UTC).

**⚾ Baseball Edge-Case Hunter notes:**

- **Condensed game video extraction:** The MLB content API nests videos deeply.
  The condensed game is typically identified by `type == "condensedGame"` in
  the highlights items. Playback URLs may include multiple formats — prefer
  the `mp4Avc` playback with the highest resolution.
- **Games without highlights:** Some completed games may not have a condensed
  game video (e.g., it hasn't been produced yet, or the game was a rainout
  that was called early). Set `condensed_game_url = None`.
- **Pitchers with no decision:** In some games (e.g., the starter is pulled
  and no reliever earns the win immediately), the API may report no winning
  pitcher. Handle nullable pitcher fields.
- **Suspended games resumed later:** A game suspended on date A and resumed on
  date B will have boxscore data under the original `gamePk`. Ensure the join
  works by `gamePk` regardless of dates.

**🤑 FinOps Miser notes:**

- Lambda memory: 512 MB should be sufficient for processing a season's worth
  of JSON (total ~50-100 MB of Bronze data). Monitor and tune down if possible.
- Lambda timeout: 300 seconds (5 minutes) is the configured max. If processing
  takes longer, consider batching by month or optimizing JSON parsing.
- The Lambda runs once per night (triggered by Bronze upload). Cost is
  effectively zero at this frequency.

**🤝 API Ethicist notes:**

- The Silver Lambda reads from S3 only — no external API calls. There are no
  ethical concerns at this layer.

The Lambda handler receives an S3 event notification with the uploaded key.
Extract the year from the key pattern to determine which Bronze files to read.
