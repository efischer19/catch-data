"""Shared data models and S3 path conventions for the medallion architecture.

See ADR-018 (Medallion Architecture) for pattern context.
"""

from catch_models.bronze import (
    BoxscoreResponse,
    ContentResponse,
    HighlightItem,
    Playback,
    ScheduleDate,
    ScheduleGame,
    ScheduleResponse,
)
from catch_models.gold import (
    GoldBoxscoreSummary,
    GoldGameSummary,
    GoldScore,
    GoldTeamInfo,
    GoldTeamSchedule,
    GoldUpcomingGames,
)
from catch_models.models import BronzeRecord, GoldMetric, SilverEntity
from catch_models.s3_paths import CatchPaths, MedallionPaths
from catch_models.silver import (
    DataCompleteness,
    SilverGame,
    SilverMasterSchedule,
    SilverProcessingErrors,
)

__all__ = [
    "BoxscoreResponse",
    "BronzeRecord",
    "ContentResponse",
    "CatchPaths",
    "DataCompleteness",
    "GoldBoxscoreSummary",
    "GoldGameSummary",
    "GoldMetric",
    "GoldScore",
    "GoldTeamInfo",
    "GoldTeamSchedule",
    "GoldUpcomingGames",
    "HighlightItem",
    "MedallionPaths",
    "Playback",
    "ScheduleDate",
    "ScheduleGame",
    "ScheduleResponse",
    "SilverGame",
    "SilverMasterSchedule",
    "SilverProcessingErrors",
    "SilverEntity",
]
