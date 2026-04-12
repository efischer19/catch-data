"""Pydantic models for the MLB Stats API game-content endpoint.

Endpoint: ``/api/v1/game/{game_pk}/content``

These models capture the editorial/media/highlights portion of the
response, with particular attention to the nested video playback URLs
(``mp4Avc``, etc.) that downstream Silver-layer processing relies on.

See ADR-018 (Medallion Architecture) for the Bronze layer's role.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

_BRONZE_CONFIG = ConfigDict(strict=True, extra="forbid")


# -- Playback / Video models -----------------------------------------------
class Playback(BaseModel):
    """A single video playback variant (e.g. mp4Avc, FLASH_2500K_1280X720)."""

    model_config = _BRONZE_CONFIG

    name: str
    url: str
    width: str | None = None
    height: str | None = None


class _Image(BaseModel):
    model_config = _BRONZE_CONFIG

    title: str | None = None
    altText: str | None = None
    cuts: dict[str, object] | None = None


class HighlightItem(BaseModel):
    """A single highlight clip (video or image) with playback URLs."""

    model_config = _BRONZE_CONFIG

    type: str
    id: str | None = None
    title: str | None = None
    description: str | None = None
    duration: str | None = None
    image: _Image | None = None
    playbacks: list[Playback]


class _HighlightsContainer(BaseModel):
    model_config = _BRONZE_CONFIG

    items: list[HighlightItem] | None = None


class _HighlightsWrapper(BaseModel):
    model_config = _BRONZE_CONFIG

    highlights: _HighlightsContainer | None = None


# -- EPG (Electronic Programme Guide) -------------------------------------
class _EpgItem(BaseModel):
    model_config = _BRONZE_CONFIG

    type: str | None = None
    title: str | None = None
    description: str | None = None
    playbacks: list[Playback] | None = None


class _EpgEntry(BaseModel):
    model_config = _BRONZE_CONFIG

    title: str
    items: list[_EpgItem]


# -- Media -----------------------------------------------------------------
class _Media(BaseModel):
    model_config = _BRONZE_CONFIG

    epg: list[_EpgEntry] | None = None
    freeGame: bool | None = None
    enhancedGame: bool | None = None


# -- Editorial -------------------------------------------------------------
class _EditorialItem(BaseModel):
    model_config = _BRONZE_CONFIG

    type: str | None = None
    headline: str | None = None
    subhead: str | None = None
    seoTitle: str | None = None
    body: str | None = None


class _EditorialSection(BaseModel):
    model_config = _BRONZE_CONFIG

    title: str | None = None
    items: list[_EditorialItem] | None = None


class _Editorial(BaseModel):
    model_config = _BRONZE_CONFIG

    recap: _EditorialSection | None = None
    articles: _EditorialSection | None = None


# -- Top-level response ----------------------------------------------------
class ContentResponse(BaseModel):
    """Full response from the game-content endpoint.

    Usage::

        data = ContentResponse.model_validate_json(raw_bytes)
    """

    model_config = _BRONZE_CONFIG

    copyright: str
    link: str
    editorial: _Editorial | None = None
    media: _Media | None = None
    highlights: _HighlightsWrapper | None = None
