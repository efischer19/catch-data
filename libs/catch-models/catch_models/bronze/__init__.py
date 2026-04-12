"""Bronze-layer Pydantic models for raw MLB Stats API responses.

These models validate and type the raw JSON payloads returned by the
MLB Stats API *without* transforming them.  They serve as the schema
contract for the Bronze layer of the medallion architecture.

See ADR-018 (Medallion Architecture) for pattern context.
"""

from catch_models.bronze.boxscore import BoxscoreResponse
from catch_models.bronze.content import ContentResponse, HighlightItem, Playback
from catch_models.bronze.schedule import ScheduleDate, ScheduleGame, ScheduleResponse

__all__ = [
    "BoxscoreResponse",
    "ContentResponse",
    "HighlightItem",
    "Playback",
    "ScheduleDate",
    "ScheduleGame",
    "ScheduleResponse",
]
