import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.errors import CrosslistError
from app.main import app
from app.platforms import AppleMusicClient, SpotifyClient


PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"


def spotify_track(track_id, name, artist, *, album="Album", duration_ms=180000, isrc=None):
    return {
        "id": track_id,
        "type": "track",
        "is_local": False,
        "name": name,
        "duration_ms": duration_ms,
        "artists": [{"name": artist}],
        "album": {
            "name": album,
            "images": [{"url": "https://example.com/spotify.jpg"}],
        },
        "external_ids": {"isrc": isrc} if isrc else {},
    }


def apple_song(song_id, name, artist, *, album="Album", duration_ms=180000, isrc=None):
    return {
        "id": song_id,
        "attributes": {
            "name": name,
            "artistName": artist,
            "albumName": album,
            "durationInMillis": duration_ms,
            "url": f"https://music.apple.com/us/song/{song_id}",
            "artwork": {"url": "https://example.com/{w}x{h}.jpg"},
            "isrc": isrc,
        },
    }


class APITests(unittest.TestCase):
    def test_health_reports_configuration_without_exposing_secrets(self):
        with patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as client:
                response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "spotify_configured": False,
                "apple_music_configured": False,
            },
        )

    def test_invalid_playlist_returns_structured_error(self):
        with TestClient(app) as client:
            response = client.post(
                "/v1/transfers/spotify-to-apple/preview",
                json={"playlist_url": "https://example.com/not-a-playlist", "storefront": "us"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_spotify_url")

    def test_preview_page_is_public_html(self):
        with TestClient(app) as client:
            for path in ("/", "/preview"):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("text/html", response.headers["content-type"])
                    body = response.text
                    self.assertIn("SPOTIFY PLAYLIST LINK", body)
                    self.assertIn("/static/preview.js", body)
                    self.assertNotIn("Sign in with Apple", body)
                    self.assertNotIn("Apple ID", body)

    def test_preview_assets_are_served(self):
        with TestClient(app) as client:
            javascript = client.get("/static/preview.js")
            stylesheet = client.get("/static/styles.css")

        self.assertEqual(javascript.status_code, 200)
        self.assertIn("/v1/transfers/spotify-to-apple/preview", javascript.text)
        self.assertIn("parseApiError", javascript.text)
        self.assertEqual(stylesheet.status_code, 200)


class MatchPreviewFlowTests(unittest.TestCase):
    def test_preview_returns_ordered_matches_and_skipped_tracks(self):
        playlist = {
            "name": "Late Night Drive",
            "description": "Test playlist",
            "external_urls": {
                "spotify": f"https://open.spotify.com/playlist/{PLAYLIST_ID}"
            },
            "images": [{"url": "https://example.com/cover.jpg"}],
            "tracks": {"total": 3},
        }
        tracks = [
            spotify_track(
                "sp1",
                "Dreams",
                "Fleetwood Mac",
                album="Rumours",
                duration_ms=257000,
                isrc="USUM71703861",
            ),
            spotify_track("sp2", "Obscure Demo", "Unknown Artist"),
            spotify_track(
                "sp3",
                "Blinding Lights",
                "The Weeknd",
                album="After Hours",
                duration_ms=200000,
            ),
        ]
        isrc_match = apple_song(
            "am1",
            "Dreams (2004 Remaster)",
            "Fleetwood Mac",
            album="Rumours",
            duration_ms=257040,
            isrc="USUM71703861",
        )
        search_match = apple_song(
            "am3",
            "Blinding Lights",
            "The Weeknd",
            album="After Hours",
            duration_ms=200040,
        )

        async def fake_items(self, playlist_id):
            for track in tracks:
                yield track

        async def fake_fallback(_client, storefront, sources):
            self.assertEqual(storefront, "us")
            by_name = {source["name"]: source for source in sources}
            self.assertIn("Obscure Demo", by_name)
            self.assertIn("Blinding Lights", by_name)
            return {
                by_name["Obscure Demo"]["position"]: (None, 0.21),
                by_name["Blinding Lights"]["position"]: (search_match, 0.91),
            }

        with (
            patch.object(SpotifyClient, "playlist", new=AsyncMock(return_value=playlist)),
            patch.object(SpotifyClient, "playlist_items", fake_items),
            patch.object(
                AppleMusicClient,
                "songs_by_isrc",
                new=AsyncMock(return_value={"USUM71703861": [isrc_match]}),
            ),
            patch.object(AppleMusicClient, "fallback_matches", fake_fallback),
            TestClient(app) as client,
        ):
            response = client.post(
                "/v1/transfers/spotify-to-apple/preview",
                json={
                    "playlist_url": f"https://open.spotify.com/playlist/{PLAYLIST_ID}",
                    "storefront": "US",
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["playlist"]["name"], "Late Night Drive")
        self.assertEqual(payload["matched_count"], 2)
        self.assertEqual(payload["unmatched_count"], 1)
        self.assertEqual(
            [track["source"]["name"] for track in payload["tracks"]],
            ["Dreams", "Obscure Demo", "Blinding Lights"],
        )

        dreams, obscure, lights = payload["tracks"]
        self.assertEqual(dreams["status"], "matched")
        self.assertEqual(dreams["match"]["method"], "isrc")
        self.assertEqual(dreams["match"]["id"], "am1")
        self.assertGreaterEqual(dreams["match"]["confidence"], 0.97)

        self.assertEqual(obscure["status"], "unmatched")
        self.assertIsNone(obscure["match"])

        self.assertEqual(lights["status"], "matched")
        self.assertEqual(lights["match"]["method"], "search")
        self.assertEqual(lights["match"]["id"], "am3")

    def test_spotify_development_mode_error_is_returned_honestly(self):
        async def restricted(self, playlist_id):
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

        with (
            patch.object(SpotifyClient, "playlist", restricted),
            TestClient(app) as client,
        ):
            response = client.post(
                "/v1/transfers/spotify-to-apple/preview",
                json={
                    "playlist_url": f"https://open.spotify.com/playlist/{PLAYLIST_ID}",
                    "storefront": "us",
                },
            )

        self.assertEqual(response.status_code, 422)
        error = response.json()["error"]
        self.assertEqual(error["code"], "spotify_playlist_access_restricted")
        self.assertIn("Development Mode", error["hint"])

    def test_missing_platform_credentials_use_existing_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with TestClient(app) as client:
                response = client.post(
                    "/v1/transfers/spotify-to-apple/preview",
                    json={
                        "playlist_url": f"https://open.spotify.com/playlist/{PLAYLIST_ID}",
                        "storefront": "us",
                    },
                )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "spotify_not_configured")


if __name__ == "__main__":
    unittest.main()
