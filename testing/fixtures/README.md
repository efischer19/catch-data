# Frozen MLB Stats API Fixtures

These fixtures are frozen JSON responses for deterministic, offline tests
across the monorepo.

## Source and privacy notes

* Fixture shapes are derived from publicly available MLB Stats API response
  structures already used in this repository's tests.
* Files are frozen for local and CI use and contain only public baseball data.
* No private credentials, tokens, or non-public metadata are included.

## Schedule fixtures

* `schedule_2025.json` — full-season-style response spanning Spring Training
  and regular-season dates; includes a Spring Training game, a doubleheader,
  a postponed game, and an extra-innings game.

## Boxscore fixtures

* `boxscore_normal.json` — routine nine-inning regular-season game
* `boxscore_doubleheader_g1.json` — doubleheader game 1
* `boxscore_doubleheader_g2.json` — doubleheader game 2
* `boxscore_extra_innings.json` — twelve-inning extra-innings game
* `boxscore_postponed.json` — postponed game with no innings played
* `boxscore_spring_training.json` — Spring Training final

## Content fixtures

* `content_with_video.json` — standard game with condensed video available
* `content_no_video.json` — game without condensed/extended highlight video
* `content_postponed.json` — postponed game with minimal content
* `content_extra_innings.json` — extra-innings game with condensed video
* `content_spring_training.json` — Spring Training game content
