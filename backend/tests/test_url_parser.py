import unittest

from app.errors import CrosslistError
from app.url_parser import spotify_playlist_id


class SpotifyPlaylistURLTests(unittest.TestCase):
    def test_parses_standard_url(self):
        self.assertEqual(
            spotify_playlist_id(
                "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=abc"
            ),
            "37i9dQZF1DXcBWIGoYBM5M",
        )

    def test_parses_localized_url(self):
        self.assertEqual(
            spotify_playlist_id(
                "https://open.spotify.com/intl-de/playlist/37i9dQZF1DXcBWIGoYBM5M"
            ),
            "37i9dQZF1DXcBWIGoYBM5M",
        )

    def test_parses_uri(self):
        self.assertEqual(
            spotify_playlist_id("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"),
            "37i9dQZF1DXcBWIGoYBM5M",
        )

    def test_rejects_non_playlist(self):
        with self.assertRaises(CrosslistError):
            spotify_playlist_id("https://open.spotify.com/track/abc")


if __name__ == "__main__":
    unittest.main()
