import re
from urllib.parse import urlparse

from .errors import CrosslistError


SPOTIFY_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


def spotify_playlist_id(value: str) -> str:
    raw = value.strip()
    if raw.startswith("spotify:playlist:"):
        candidate = raw.removeprefix("spotify:playlist:").split("?", 1)[0]
    else:
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
            "open.spotify.com",
            "www.open.spotify.com",
        }:
            raise CrosslistError(
                code="invalid_spotify_url",
                message="Paste a valid public Spotify playlist link.",
                hint="The link should look like https://open.spotify.com/playlist/…",
            )
        segments = [segment for segment in parsed.path.split("/") if segment]
        try:
            playlist_index = segments.index("playlist")
            candidate = segments[playlist_index + 1]
        except (ValueError, IndexError) as exc:
            raise CrosslistError(
                code="invalid_spotify_url",
                message="This Spotify link is not a playlist.",
                hint="Open the playlist in Spotify, choose Share, then Copy link.",
            ) from exc

    if not SPOTIFY_ID_PATTERN.fullmatch(candidate):
        raise CrosslistError(
            code="invalid_spotify_url",
            message="This Spotify playlist link has an invalid identifier.",
        )
    return candidate

