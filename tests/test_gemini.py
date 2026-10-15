import io
import json
import os
import unittest
import urllib.error
from unittest import mock

from backend import ai

MSGS = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "USR"}]


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def reply(obj):
    return FakeResp(json.dumps(obj).encode())


def http_error(code, body=None):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(json.dumps(body or {}).encode()))


class GeminiTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "SECRET-KEY", "GEMINI_MODEL": ""})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_request_shape_and_key_only_in_header(self):
        out = {"candidates": [{"content": {"parts": [{"text": '{"exercises": []}'}]}}]}
        with mock.patch("urllib.request.urlopen", return_value=reply(out)) as op:
            self.assertEqual(ai.gemini_chat(MSGS), '{"exercises": []}')
        req = op.call_args[0][0]
        self.assertNotIn("SECRET-KEY", req.full_url)
        self.assertEqual(req.get_header("X-goog-api-key"), "SECRET-KEY")
        self.assertIn("gemini-3.5-flash:generateContent", req.full_url)
        body = json.loads(req.data)
        self.assertEqual(body["systemInstruction"]["parts"][0]["text"], "SYS")
        self.assertEqual(body["contents"], [{"role": "user", "parts": [{"text": "USR"}]}])
        self.assertEqual(body["generationConfig"]["responseMimeType"], "application/json")

    def test_missing_key_gives_setup_hint(self):
        self.assertTrue(ai.active_model().startswith("Gemini"))
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            with self.assertRaises(ai.AiUnavailable) as cm:
                ai.default_chat(MSGS)
        self.assertIn("GEMINI_API_KEY", cm.exception.message)

    def test_errors_are_friendly_and_do_not_leak_key(self):
        for code, text in ((429, "ліміт"), (403, "GEMINI_API_KEY"), (500, "перевантажений")):
            with mock.patch("urllib.request.urlopen", side_effect=http_error(code)):
                with self.assertRaises(ai.AiUnavailable) as cm:
                    ai.gemini_chat(MSGS)
            self.assertIn(text, cm.exception.message)
            self.assertNotIn("SECRET-KEY", cm.exception.message)
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(ai.AiUnavailable):
                ai.gemini_chat(MSGS)

    def test_falls_back_to_next_model_when_overloaded(self):
        out = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
        with mock.patch("urllib.request.urlopen", side_effect=[http_error(503), reply(out)]) as op:
            self.assertEqual(ai.gemini_chat(MSGS), "{}")
        self.assertIn("gemini-3.5-flash-lite", op.call_args[0][0].full_url)

    def test_explicit_model_has_no_fallback(self):
        with mock.patch.dict(os.environ, {"GEMINI_MODEL": "my-model"}):
            with mock.patch("urllib.request.urlopen", side_effect=http_error(503)) as op:
                with self.assertRaises(ai.AiUnavailable):
                    ai.gemini_chat(MSGS)
        self.assertEqual(op.call_count, 1)

    def test_blocked_or_empty_response(self):
        with mock.patch("urllib.request.urlopen", return_value=reply({"promptFeedback": {"blockReason": "SAFETY"}})):
            with self.assertRaises(ai.AiUnavailable) as cm:
                ai.gemini_chat(MSGS)
        self.assertIn("SAFETY", cm.exception.message)

    def test_generate_workout_end_to_end_with_gemini(self):
        plan = {"title": "Ноги", "notes": "", "exercises": [{"name": "Болгарські присідання", "sets": [{"reps": 8, "weight_kg": 20}]}]}
        out = {"candidates": [{"content": {"parts": [{"text": json.dumps(plan)}]}}]}
        with mock.patch("urllib.request.urlopen", return_value=reply(out)):
            draft = ai.generate_workout("день ніг", {}, ["Болгарські присідання"])
        self.assertEqual(draft["exercises"][0]["name"], "Болгарські присідання")


if __name__ == "__main__":
    unittest.main()
