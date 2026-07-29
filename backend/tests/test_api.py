import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


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


if __name__ == "__main__":
    unittest.main()

