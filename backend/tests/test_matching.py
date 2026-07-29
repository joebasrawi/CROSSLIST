import unittest

from app.matching import best_candidate, candidate_score, normalize


class MatchingTests(unittest.TestCase):
    def test_normalizes_versions_and_features(self):
        self.assertEqual(normalize("Midnight (feat. Someone)"), "midnight")
        self.assertEqual(normalize("Midnight - Remastered 2024"), "midnight")

    def test_prefers_correct_candidate(self):
        source = {
            "name": "Dreams",
            "artist": "Fleetwood Mac",
            "album": "Rumours",
            "duration_ms": 257000,
        }
        wrong = {
            "id": "1",
            "attributes": {
                "name": "Dreams",
                "artistName": "The Cranberries",
                "albumName": "Everybody Else Is Doing It, So Why Can't We?",
                "durationInMillis": 270000,
            },
        }
        correct = {
            "id": "2",
            "attributes": {
                "name": "Dreams (2004 Remaster)",
                "artistName": "Fleetwood Mac",
                "albumName": "Rumours",
                "durationInMillis": 257040,
            },
        }
        candidate, score = best_candidate(source, [wrong, correct])
        self.assertEqual(candidate["id"], "2")
        self.assertGreater(score, 0.9)

    def test_duration_penalizes_bad_versions(self):
        source = {"name": "Song", "artist": "Artist", "album": "Album", "duration_ms": 180000}
        close = {"attributes": {"name": "Song", "artistName": "Artist", "albumName": "Album", "durationInMillis": 181000}}
        far = {"attributes": {"name": "Song", "artistName": "Artist", "albumName": "Album", "durationInMillis": 260000}}
        self.assertGreater(candidate_score(source, close), candidate_score(source, far))


if __name__ == "__main__":
    unittest.main()

