import unittest

from backend.services import EXERCISE_CATALOG
from backend.videos import EXERCISE_VIDEOS
from tests.helpers import ApiTestCase


class BuiltInVideoTests(unittest.TestCase):
    def test_every_catalog_exercise_has_a_video(self):
        self.assertEqual([n for n in EXERCISE_CATALOG if n not in EXERCISE_VIDEOS], [])
        self.assertIn("Болгарські присідання", EXERCISE_VIDEOS)


class VideosApiTests(ApiTestCase):
    default_username = "alice"

    def test_videos_endpoint_requires_auth(self):
        self.assertEqual(self.call("GET", "/api/videos", token=None)[0], 401)

    def test_videos_endpoint_returns_catalog_and_is_read_only(self):
        st, r = self.call("GET", "/api/videos")
        self.assertEqual(st, 200)
        item = next(i for i in r["items"] if i["name_key"] == "болгарські присідання")
        self.assertEqual((item["exercise"], len(item["video_id"])), ("Болгарські присідання", 11))
        for method in ("PUT", "DELETE", "POST"):
            with self.subTest(method=method):
                self.assertEqual(self.call(method, "/api/videos", {})[0], 405)


if __name__ == "__main__":
    unittest.main()
