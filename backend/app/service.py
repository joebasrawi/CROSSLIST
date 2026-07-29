from typing import Any

from .matching import best_candidate
from .models import (
    AppleMusicMatch,
    PlaylistSummary,
    PreviewTrack,
    SourceTrack,
    TransferPreview,
)
from .platforms import AppleMusicClient, SpotifyClient


def _artwork_url(images: list[dict[str, Any]] | None) -> str | None:
    if not images:
        return None
    return images[0].get("url")


def _source_track(item: dict[str, Any], position: int) -> dict[str, Any]:
    artists = ", ".join(artist.get("name", "") for artist in item.get("artists", []))
    album = item.get("album") or {}
    return {
        "position": position,
        "spotify_id": item.get("id", ""),
        "name": item.get("name", "Unknown track"),
        "artist": artists or "Unknown artist",
        "album": album.get("name"),
        "duration_ms": item.get("duration_ms"),
        "isrc": (item.get("external_ids") or {}).get("isrc"),
        "artwork_url": _artwork_url(album.get("images")),
    }


def _apple_match(
    item: dict[str, Any], confidence: float, method: str
) -> AppleMusicMatch:
    attributes = item.get("attributes", {})
    artwork = attributes.get("artwork") or {}
    artwork_template = artwork.get("url")
    artwork_url = (
        artwork_template.replace("{w}", "300").replace("{h}", "300")
        if artwork_template
        else None
    )
    return AppleMusicMatch(
        id=item["id"],
        name=attributes.get("name", "Unknown track"),
        artist=attributes.get("artistName", "Unknown artist"),
        album=attributes.get("albumName"),
        duration_ms=attributes.get("durationInMillis"),
        url=attributes.get("url"),
        artwork_url=artwork_url,
        confidence=confidence,
        method=method,
    )


async def build_spotify_to_apple_preview(
    playlist_id: str,
    storefront: str,
    spotify: SpotifyClient,
    apple_music: AppleMusicClient,
) -> TransferPreview:
    playlist = await spotify.playlist(playlist_id)
    source_tracks = [
        _source_track(item, position)
        async for position, item in _enumerate_async(spotify.playlist_items(playlist_id))
    ]

    isrc_map = await apple_music.songs_by_isrc(
        storefront, [track["isrc"] for track in source_tracks if track.get("isrc")]
    )
    matches: dict[int, tuple[dict[str, Any], float, str]] = {}
    unmatched_sources: list[dict[str, Any]] = []

    for source in source_tracks:
        candidates = isrc_map.get((source.get("isrc") or "").upper(), [])
        candidate, score = best_candidate(source, candidates)
        if candidate:
            matches[source["position"]] = (candidate, max(score, 0.97), "isrc")
        else:
            unmatched_sources.append(source)

    if unmatched_sources:
        fallbacks = await apple_music.fallback_matches(storefront, unmatched_sources)
        for position, (candidate, score) in fallbacks.items():
            if candidate and score >= 0.72:
                matches[position] = (candidate, score, "search")

    preview_tracks: list[PreviewTrack] = []
    for source in source_tracks:
        match_data = matches.get(source["position"])
        preview_tracks.append(
            PreviewTrack(
                source=SourceTrack(**source),
                status="matched" if match_data else "unmatched",
                match=(
                    _apple_match(match_data[0], match_data[1], match_data[2])
                    if match_data
                    else None
                ),
            )
        )

    items_summary = playlist.get("items") or playlist.get("tracks") or {}
    matched_count = sum(track.status == "matched" for track in preview_tracks)
    return TransferPreview(
        playlist=PlaylistSummary(
            spotify_id=playlist_id,
            name=playlist.get("name", "Spotify Playlist"),
            description=playlist.get("description"),
            source_url=(playlist.get("external_urls") or {}).get(
                "spotify", f"https://open.spotify.com/playlist/{playlist_id}"
            ),
            artwork_url=_artwork_url(playlist.get("images")),
            total_tracks=items_summary.get("total", len(source_tracks)),
        ),
        tracks=preview_tracks,
        matched_count=matched_count,
        unmatched_count=len(preview_tracks) - matched_count,
        storefront=storefront.lower(),
    )


async def _enumerate_async(iterator):
    position = 0
    async for item in iterator:
        yield position, item
        position += 1

