import asyncio
import base64
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .config import Settings
from .errors import CrosslistError
from .matching import best_candidate


class SpotifyClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client
        self._access_token: str | None = None

    async def _token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.settings.spotify_configured:
            raise CrosslistError(
                code="spotify_not_configured",
                message="Spotify access is not configured on this CROSSLIST server.",
                status_code=503,
                hint="Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in Railway.",
            )
        credentials = f"{self.settings.spotify_client_id}:{self.settings.spotify_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        response = await self.client.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {encoded}"},
            data={"grant_type": "client_credentials"},
        )
        if response.status_code >= 400:
            raise CrosslistError(
                code="spotify_auth_failed",
                message="CROSSLIST could not authenticate with Spotify.",
                status_code=502,
            )
        self._access_token = response.json()["access_token"]
        return self._access_token

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._token()
        response = await self.client.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 403:
            raise CrosslistError(
                code="spotify_playlist_access_restricted",
                message="Spotify did not allow CROSSLIST to read this playlist.",
                status_code=422,
                hint=(
                    "Spotify Development Mode currently limits playlist contents to the "
                    "authenticated owner's or collaborator's playlists. Production use needs "
                    "approved Spotify access."
                ),
            )
        if response.status_code == 404:
            raise CrosslistError(
                code="spotify_playlist_not_found",
                message="Spotify could not find that playlist.",
                status_code=404,
                hint="Confirm that the playlist is public and the link still works.",
            )
        if response.status_code == 429:
            raise CrosslistError(
                code="spotify_rate_limited",
                message="Spotify is receiving too many requests. Try again shortly.",
                status_code=429,
            )
        if response.status_code >= 400:
            raise CrosslistError(
                code="spotify_request_failed",
                message="Spotify could not provide this playlist right now.",
                status_code=502,
            )
        return response.json()

    async def playlist(self, playlist_id: str) -> dict[str, Any]:
        return await self._get(
            f"https://api.spotify.com/v1/playlists/{playlist_id}",
            params={
                "fields": "id,name,description,external_urls,images,items(total)"
            },
        )

    async def playlist_items(self, playlist_id: str) -> AsyncIterator[dict[str, Any]]:
        url: str | None = f"https://api.spotify.com/v1/playlists/{playlist_id}/items"
        params: dict[str, Any] | None = {"limit": 50, "additional_types": "track"}
        while url:
            page = await self._get(url, params=params)
            for wrapper in page.get("items", []):
                item = wrapper.get("item") or wrapper.get("track")
                if item and item.get("type") == "track" and not item.get("is_local"):
                    yield item
            url = page.get("next")
            params = None


class AppleMusicClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client

    def _headers(self) -> dict[str, str]:
        if not self.settings.apple_music_configured:
            raise CrosslistError(
                code="apple_music_not_configured",
                message="Apple Music catalog access is not configured on this CROSSLIST server.",
                status_code=503,
                hint="Add APPLE_MUSIC_DEVELOPER_TOKEN in Railway.",
            )
        return {"Authorization": f"Bearer {self.settings.apple_music_developer_token}"}

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.get(url, params=params, headers=self._headers())
        if response.status_code == 401:
            raise CrosslistError(
                code="apple_music_auth_failed",
                message="The Apple Music developer token is invalid or expired.",
                status_code=503,
            )
        if response.status_code == 429:
            raise CrosslistError(
                code="apple_music_rate_limited",
                message="Apple Music is receiving too many requests. Try again shortly.",
                status_code=429,
            )
        if response.status_code >= 400:
            raise CrosslistError(
                code="apple_music_request_failed",
                message="Apple Music catalog matching failed.",
                status_code=502,
            )
        return response.json()

    async def songs_by_isrc(
        self, storefront: str, isrcs: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        unique_isrcs = list(dict.fromkeys(value.upper() for value in isrcs if value))
        for index in range(0, len(unique_isrcs), 25):
            batch = unique_isrcs[index : index + 25]
            payload = await self._get(
                f"https://api.music.apple.com/v1/catalog/{storefront}/songs",
                {"filter[isrc]": ",".join(batch)},
            )
            by_id = {item["id"]: item for item in payload.get("data", [])}
            filters = payload.get("meta", {}).get("filters", {}).get("isrc", {})
            for isrc in batch:
                references = filters.get(isrc, [])
                matches = [by_id[ref["id"]] for ref in references if ref.get("id") in by_id]
                if not matches:
                    matches = [
                        item
                        for item in payload.get("data", [])
                        if item.get("attributes", {}).get("isrc", "").upper() == isrc
                    ]
                result[isrc] = matches
        return result

    async def search_song(
        self, storefront: str, source: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, float]:
        query = " ".join(filter(None, [source.get("name"), source.get("artist")]))
        payload = await self._get(
            f"https://api.music.apple.com/v1/catalog/{storefront}/search",
            {"term": query, "types": "songs", "limit": 5},
        )
        candidates = payload.get("results", {}).get("songs", {}).get("data", [])
        return best_candidate(source, candidates)

    async def fallback_matches(
        self, storefront: str, sources: list[dict[str, Any]]
    ) -> dict[int, tuple[dict[str, Any] | None, float]]:
        semaphore = asyncio.Semaphore(5)

        async def match(source: dict[str, Any]) -> tuple[int, dict[str, Any] | None, float]:
            async with semaphore:
                candidate, score = await self.search_song(storefront, source)
                return source["position"], candidate, score

        results = await asyncio.gather(*(match(source) for source in sources))
        return {position: (candidate, score) for position, candidate, score in results}
