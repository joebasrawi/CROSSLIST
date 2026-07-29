from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PreviewRequest(BaseModel):
    playlist_url: str = Field(min_length=1, max_length=2048)
    storefront: str = Field(default="us", pattern=r"^[a-zA-Z]{2}$")


class SourceTrack(BaseModel):
    position: int
    spotify_id: str
    name: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    isrc: str | None = None
    artwork_url: HttpUrl | None = None


class AppleMusicMatch(BaseModel):
    id: str
    name: str
    artist: str
    album: str | None = None
    duration_ms: int | None = None
    url: HttpUrl | None = None
    artwork_url: HttpUrl | None = None
    confidence: float = Field(ge=0, le=1)
    method: Literal["isrc", "search"]


class PreviewTrack(BaseModel):
    source: SourceTrack
    status: Literal["matched", "unmatched"]
    match: AppleMusicMatch | None = None


class PlaylistSummary(BaseModel):
    spotify_id: str
    name: str
    description: str | None = None
    source_url: HttpUrl
    artwork_url: HttpUrl | None = None
    total_tracks: int


class TransferPreview(BaseModel):
    playlist: PlaylistSummary
    tracks: list[PreviewTrack]
    matched_count: int
    unmatched_count: int
    storefront: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    spotify_configured: bool
    apple_music_configured: bool


class ErrorBody(BaseModel):
    code: str
    message: str
    hint: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

