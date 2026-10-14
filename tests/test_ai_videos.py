import json
import unittest

from backend import ai
from backend.services import EXERCISE_CATALOG
from backend.videos import EXERCISE_VIDEOS
from tests.helpers import Api, make_app

GOOD = {"title": "Ноги", "notes": "Розминка", "exercises": [
    {"name": "Присідання зі штангою", "sets": [{"reps": 8, "weight_kg": 60}, {"reps": 8, "weight_kg": 60}]}]}


class BuiltInVideoTests(unittest.TestCase):
    def test_every_catalog_exercise_has_a_video(self):
        self.assertEqual([n for n in EXERCISE_CATALOG if n not in EXERCISE_VIDEOS], [])
        self.assertIn("Болгарські присідання", EXERCISE_VIDEOS)


class SanitizeTests(unittest.TestCase):
    def test_clamps_and_drops_garbage(self):
        plan = ai.sanitize_plan({"title": "x" * 99, "exercises": [
            {"name": "Жим", "sets": [{"reps": 9999, "weight_kg": -5}, {"reps": "abc", "weight": "40"}, "junk"]},
            {"name": "", "sets": [{"reps": 5}]}, {"name": "Без підходів", "sets": []}, "junk"]})
        self.assertEqual(len(plan["title"]), 60)
        self.assertEqual(plan["exercises"], [{"name": "Жим", "sets": [{"reps": 100, "weight_kg": 0}, {"reps": 10, "weight_kg": 40}]}])

    def test_json_wrapped_in_text_and_failures(self):
        self.assertEqual(len(ai.sanitize_plan("Ось: " + json.dumps(GOOD) + " Успіхів!")["exercises"]), 1)
        for bad in ("не json", "{}", {"exercises": []}, {"exercises": "x"}):
            with self.assertRaises(ai.AiUnavailable):
                ai.sanitize_plan(bad)


class TitleAndWeightTests(unittest.TestCase):
    def plan(self, name="Жим лежачи", reps=10, kg=60):
        return {"title": "T", "notes": "", "exercises": [{"name": name, "sets": [{"reps": reps, "weight_kg": kg}]}]}

    def test_long_title_is_cut_at_word_boundary(self):
        title = "Функціональне тренування на все тіло для розвитку витривалості та сили"
        out = ai.sanitize_plan({"title": title, "exercises": self.plan()["exercises"]})["title"]
        self.assertLessEqual(len(out), 60)
        self.assertTrue(title.startswith(out) and title[len(out)] == " ", out)

    def test_weight_from_history_not_from_model(self):
        records = [{"exercise": "Жим лежачи", "best_1rm": 100.0}]
        out = ai.personalize_weights(self.plan(reps=10, kg=200), records)
        ex = out["exercises"][0]
        # 100 / (1 + 12/30) = 71.4 kg, nearest multiple of 2.5 kg is 72.5
        self.assertEqual((ex["sets"][0]["weight_kg"], ex["weight_source"]), (72.5, "history"))

    def test_no_history_means_no_invented_weight(self):
        ex = ai.personalize_weights(self.plan(), [])["exercises"][0]
        self.assertEqual((ex["sets"][0]["weight_kg"], ex["weight_source"]), (0, "needs"))

    def test_bodyweight_exercise_is_left_alone(self):
        ex = ai.personalize_weights(self.plan("Підтягування", kg=0), [{"exercise": "Підтягування", "best_1rm": 0.0}])["exercises"][0]
        self.assertEqual((ex["sets"][0]["weight_kg"], ex["weight_source"]), (0, None))


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.reply = json.dumps(GOOD)
        self.prompts = []

        def chat(messages):
            self.prompts.append(messages)
            return self.reply
        self.api = Api(self.app, ai_chat=chat)
        self.tok = self.signup("alice")
        self.tok2 = self.signup("bob")

    def signup(self, name):
        return self.api.handle("POST", "/api/auth/register", None, {"username": name, "password": "secret123"})[1]["token"]

    def call(self, method, path, body=None, query=None, token=None):
        return self.api.handle(method, path, query, body, token or self.tok)

    def test_ai_requires_auth_and_prompt(self):
        self.assertEqual(self.api.handle("POST", "/api/ai/workout", None, {"prompt": "x"}, None)[0], 401)
        self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": "  "})[0], 400)
        self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": "x" * 501})[0], 400)

    def test_ai_draft_uses_profile_and_is_not_saved(self):
        self.call("PATCH", "/api/me", {"sport": "Пауерліфтинг", "level": "середній"})
        st, r = self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})
        self.assertEqual(st, 200)
        self.assertEqual(r["draft"]["exercises"][0]["name"], "Присідання зі штангою")
        self.assertIn("Пауерліфтинг", self.prompts[0][1]["content"])
        self.assertEqual(self.call("GET", "/api/me/records")[1]["items"], [])

    def test_ai_failure_is_503(self):
        self.reply = "не json"
        self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})[0], 503)

        def down(messages):
            raise ai.AiUnavailable("Gemini недоступний")
        self.api.ai_chat = down
        st, r = self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})
        self.assertEqual((st, r["error"]), (503, "Gemini недоступний"))

    def test_videos_endpoint_is_read_only_and_authenticated(self):
        self.assertEqual(self.api.handle("GET", "/api/videos", None, None, None)[0], 401)
        st, r = self.call("GET", "/api/videos")
        self.assertEqual(st, 200)
        item = next(i for i in r["items"] if i["name_key"] == "болгарські присідання")
        self.assertEqual((item["exercise"], len(item["video_id"])), ("Болгарські присідання", 11))
        for method in ("PUT", "DELETE", "POST"):
            self.assertEqual(self.call(method, "/api/videos", {})[0], 405)

if __name__ == "__main__":
    unittest.main()
