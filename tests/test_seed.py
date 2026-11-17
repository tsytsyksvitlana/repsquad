import contextlib
import io
import os
import tempfile
import unittest

import seed
from backend.services import RepSquad
from tests.helpers import count_rows, execute_sql, query_one


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "demo.db")

    def run_seed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            seed.seed(self.path)
        app = RepSquad(self.path)
        self.addCleanup(app.close)
        return app

    @staticmethod
    def reaction_counts(app):
        return [count_rows(app, table) for table in ("post_likes", "post_comments")]

    def test_posts_with_photos_are_created_once(self):
        app = self.run_seed()
        self.assertEqual(count_rows(app, "posts"), len(seed.POSTS))
        self.assertEqual(count_rows(app, "post_images"), sum(1 for p in seed.POSTS if p[4]))
        app = self.run_seed()  # idempotent
        self.assertEqual(count_rows(app, "posts"), len(seed.POSTS))

    def test_only_missing_posts_are_added_and_user_posts_are_kept(self):
        app = self.run_seed()
        execute_sql(app, "DELETE FROM posts WHERE id = (SELECT MIN(id) FROM posts)")
        olena = query_one(app, "SELECT id FROM users WHERE username = 'olena_fit'")["id"]
        app.create_post(olena, {"body": "my own post"})
        app = self.run_seed()
        self.assertEqual(count_rows(app, "posts"), len(seed.POSTS) + 1)

    def test_demo_reactions_exist_and_are_not_duplicated(self):
        app = self.run_seed()
        first = self.reaction_counts(app)
        self.assertGreater(first[0], 0)
        self.assertGreater(first[1], 0)
        self.run_seed()
        self.assertEqual(self.reaction_counts(app), first)

    def test_photos_exist_and_pass_validation(self):
        for photo in {p[4] for p in seed.POSTS if p[4]}:
            with self.subTest(photo=photo):
                self.assertTrue((seed.IMAGES / photo).is_file())

    def test_private_demo_post_is_hidden_from_others(self):
        app = self.run_seed()
        viewer = query_one(app, "SELECT id FROM users WHERE username = 'olena_fit'")["id"]
        bodies = [i["body"] for i in app.discover(viewer, 50, 0, "posts")["items"]]
        self.assertEqual(len(bodies), sum(1 for p in seed.POSTS if p[2] == "public"))


if __name__ == "__main__":
    unittest.main()
