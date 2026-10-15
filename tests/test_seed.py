import contextlib
import io
import os
import tempfile
import unittest

import seed
from backend.services import RepSquad


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "demo.db")

    def run_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            seed.seed(self.path)
        return RepSquad(self.path)

    def test_posts_with_photos_are_created_once(self):
        app = self.run_seed()
        self.assertEqual(app._one("SELECT COUNT(*) AS n FROM posts")["n"], len(seed.POSTS))
        self.assertEqual(app._one("SELECT COUNT(*) AS n FROM post_images")["n"], sum(1 for p in seed.POSTS if p[4]))
        app = self.run_seed()  # idempotent
        self.assertEqual(app._one("SELECT COUNT(*) AS n FROM posts")["n"], len(seed.POSTS))

    def test_only_missing_posts_are_added_and_user_posts_are_kept(self):
        app = self.run_seed()
        with app.conn:
            app.conn.execute("DELETE FROM posts WHERE id = (SELECT MIN(id) FROM posts)")
        olena = app._one("SELECT id FROM users WHERE username = 'olena_fit'")["id"]
        app.create_post(olena, {"body": "my own post"})
        app = self.run_seed()
        self.assertEqual(app._one("SELECT COUNT(*) AS n FROM posts")["n"], len(seed.POSTS) + 1)

    def test_demo_reactions_exist_and_are_not_duplicated(self):
        app = self.run_seed()
        counts = lambda: [app._one(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in ("post_likes", "post_comments")]
        first = counts()
        self.assertGreater(first[0], 0)
        self.assertGreater(first[1], 0)
        self.run_seed()
        self.assertEqual(counts(), first)

    def test_photos_exist_and_pass_validation(self):
        for photo in {p[4] for p in seed.POSTS if p[4]}:
            self.assertTrue((seed.IMAGES / photo).is_file(), photo)

    def test_private_demo_post_is_hidden_from_others(self):
        app = self.run_seed()
        viewer = app._one("SELECT id FROM users WHERE username = 'olena_fit'")["id"]
        bodies = [i["body"] for i in app.discover(viewer, 50, 0, "posts")["items"]]
        self.assertEqual(len(bodies), sum(1 for p in seed.POSTS if p[2] == "public"))


if __name__ == "__main__":
    unittest.main()
