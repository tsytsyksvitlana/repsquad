import json
import unittest

from backend import ai
from tests.helpers import ApiTestCase

GOOD_PLAN = {
    "title": "Ноги",
    "notes": "Розминка",
    "exercises": [{"name": "Присідання зі штангою", "sets": [{"reps": 8, "weight_kg": 60}, {"reps": 8, "weight_kg": 60}]}],
}


class SanitizeTests(unittest.TestCase):
    def test_clamps_and_drops_garbage(self):
        plan = ai.sanitize_plan({"title": "x" * 99, "exercises": [
            {"name": "Жим", "sets": [{"reps": 9999, "weight_kg": -5}, {"reps": "abc", "weight": "40"}, "junk"]},
            {"name": "", "sets": [{"reps": 5}]}, {"name": "Без підходів", "sets": []}, "junk"]})
        self.assertEqual(len(plan["title"]), 60)
        self.assertEqual(plan["exercises"], [{"name": "Жим", "sets": [{"reps": 100, "weight_kg": 0}, {"reps": 10, "weight_kg": 40}]}])

    def test_extracts_json_wrapped_in_text(self):
        plan = ai.sanitize_plan("Ось: " + json.dumps(GOOD_PLAN) + " Успіхів!")
        self.assertEqual(len(plan["exercises"]), 1)

    def test_rejects_malformed_plan_payloads(self):
        for bad in ("не json", "{}", {"exercises": []}, {"exercises": "x"}):
            with self.subTest(bad=bad), self.assertRaises(ai.AiUnavailable):
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


class AiWorkoutApiTests(ApiTestCase):
    default_username = "alice"

    def make_ai_chat(self):
        self.reply = json.dumps(GOOD_PLAN)
        self.prompts = []

        def chat(messages):
            self.prompts.append(messages)
            return self.reply

        return chat

    def test_ai_requires_auth(self):
        self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": "x"}, token=None)[0], 401)

    def test_ai_rejects_invalid_prompts(self):
        for prompt in ("", "  ", "x" * 501, None):
            with self.subTest(prompt=repr(prompt)):
                self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": prompt})[0], 400)

    def test_ai_draft_uses_profile_and_is_not_saved(self):
        self.call("PATCH", "/api/me", {"sport": "Пауерліфтинг", "level": "середній"})
        st, r = self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})
        self.assertEqual(st, 200)
        self.assertEqual(r["draft"]["exercises"][0]["name"], "Присідання зі штангою")
        self.assertIn("Пауерліфтинг", self.prompts[0][1]["content"])
        self.assertEqual(self.call("GET", "/api/me/records")[1]["items"], [])

    def test_invalid_ai_output_returns_503(self):
        self.reply = "не json"
        self.assertEqual(self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})[0], 503)

    def test_ai_provider_unavailable_returns_503_with_message(self):
        def down(_messages):
            raise ai.AiUnavailable("Gemini недоступний")

        self.api.ai_chat = down
        st, r = self.call("POST", "/api/ai/workout", {"prompt": "день ніг"})
        self.assertEqual((st, r["error"]), (503, "Gemini недоступний"))


if __name__ == "__main__":
    unittest.main()
