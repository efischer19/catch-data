# catch-models

> Shared data models and S3 path conventions for the medallion architecture.

## Purpose

This library provides the shared data contracts and path conventions used
across the medallion architecture pipeline stages. It demonstrates:

* Pydantic models for data validation at each pipeline layer
* S3 key path conventions (`bronze/`, `silver/`, `gold/`)
* Path dependency pattern for monorepo consumers
* Testing with pytest

See [ADR-018](../../meta/adr/ADR-018-medallion_architecture.md) for pattern
context.

## Installation

From an application in the monorepo, add a path dependency:

```toml
[tool.poetry.dependencies]
catch-models = { path = "../../libs/catch-models", develop = true }
```

Then install:

```bash
poetry install
```

## Usage

### Data Models

```python
from catch_models import (
    BronzeRecord,
    DataCompleteness,
    GoldMetric,
    SilverGame,
    SilverMasterSchedule,
    SilverEntity,
)

# Bronze — raw ingested data
record = BronzeRecord(
    source="api-source",
    raw_data={"user_id": "123", "action": "login"},
)

# Silver — cleaned and validated data
entity = SilverEntity(entity_id="usr-123", name="Example User")

silver_game = SilverGame(
    gamePk=745678,
    date="2026-07-04T17:05:00Z",
    game_type="R",
    away_team_id=111,
    away_team_name="Boston Red Sox",
    away_team_abbreviation="BOS",
    home_team_id=147,
    home_team_name="New York Yankees",
    home_team_abbreviation="NYY",
    venue_id=3313,
    venue_name="Yankee Stadium",
    status="Final",
    status_detail="Final",
    innings=9,
    away_runs=3,
    away_hits=7,
    away_errors=1,
    home_runs=5,
    home_hits=9,
    home_errors=0,
    winning_pitcher_name="Gerrit Cole",
    losing_pitcher_name="Chris Sale",
    source_updated_at="2026-07-04T21:00:00Z",
    data_completeness=DataCompleteness.FULL,
)

master_schedule = SilverMasterSchedule(year=2026, games=[silver_game])

# Gold — business-ready metrics
metric = GoldMetric(
    metric_name="daily-active-users",
    value=1234.5,
    dimensions={"region": "us-east-1"},
)
```

### S3 Path Conventions

```python
from datetime import date
from catch_models import MedallionPaths

paths = MedallionPaths("my-project-data-dev")

paths.bronze("api-source", date(2026, 1, 15))
# => "bronze/api-source/2026-01-15/"

paths.silver("users", date(2026, 1, 15))
# => "silver/users/2026-01-15/"

paths.gold("daily-active-users")
# => "gold/served/daily-active-users/"
```

## API

### Models

* **`BronzeRecord`** — Raw ingested record with source metadata
* **`SilverEntity`** — Generic Silver-layer example model
* **`SilverGame`** — Silver-layer cleaned MLB game record
* **`SilverMasterSchedule`** — Season container for Silver games
* **`GoldMetric`** — Aggregated business metric (generic skeleton)
* **`GoldTeamInfo`** — Lightweight team identity (id, name, abbreviation, league, division)
* **`GoldScore`** — Lightweight run totals (away / home) for display
* **`GoldBoxscoreSummary`** — Full R/H/E line + pitching decisions for completed games
* **`GoldGameSummary`** — Single-game view model consumed by the catch-app frontend
* **`GoldTeamSchedule`** — Full season schedule for one team (`gold/team_{id}.json`)
* **`GoldUpcomingGames`** — Rolling-window view of near-term games (`gold/upcoming_games.json`)

### Utilities

* **`MedallionPaths(bucket_name)`** — S3 key prefix generator
  * `.bronze(source, date)` → `"bronze/{source}/{date}/"`
  * `.silver(entity, date)` → `"silver/{entity}/{date}/"`
  * `.gold(metric_name)` → `"gold/served/{metric_name}/"`
  * `.s3_uri(key_prefix)` → `"s3://{bucket}/{key_prefix}"`

## Development

```bash
cd libs/catch-models
poetry install
poetry run python -m catch_models.schema
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
```

## Dependencies

* **[Pydantic](https://docs.pydantic.dev/)** — Data validation using
  Python type annotations
