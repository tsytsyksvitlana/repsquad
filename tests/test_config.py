import os
import unittest
from datetime import timedelta
from unittest import mock

from backend import ai, config

ENV_KEYS = ("REPSQUAD_DB", "REPSQUAD_HOST", "REPSQUAD_PORT", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL")


class ConfigTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ENV_KEYS:
            os.environ.pop(key, None)

    def test_defaults_match_the_original_values(self):
        self.assertEqual(config.db_path(), "repsquad.db")
        self.assertEqual(config.host(), "127.0.0.1")
        self.assertEqual(config.port(), 8000)
        self.assertEqual(config.gemini_key(), "")
        self.assertEqual(config.gemini_models(), ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"])
        self.assertEqual(config.GEMINI_URL, "https://generativelanguage.googleapis.com/v1beta/models")
        self.assertEqual(config.GEMINI_TIMEOUT, 40)
        self.assertEqual(config.SESSION_TTL, timedelta(days=30))
        self.assertEqual(config.PAGE_MAX, 50)
        self.assertEqual(config.PBKDF2_ITERATIONS, 200_000)
        self.assertEqual(config.AVATAR_MAX_AGE, 31536000)
        self.assertEqual(config.POST_IMAGE_MAX_AGE, 3600)
        self.assertEqual(config.FRONTEND_DIST, config.ROOT / "frontend" / "dist")

    def test_environment_overrides(self):
        os.environ.update(REPSQUAD_DB="other.db", REPSQUAD_HOST="0.0.0.0", REPSQUAD_PORT="9001", GEMINI_MODEL="m1")
        self.assertEqual(config.db_path(), "other.db")
        self.assertEqual(config.host(), "0.0.0.0")
        self.assertEqual(config.port(), 9001)
        self.assertEqual(config.gemini_models(), ["m1"])

    def test_gemini_key_prefers_gemini_over_google_key(self):
        os.environ["GOOGLE_API_KEY"] = "g"
        self.assertEqual(config.gemini_key(), "g")
        os.environ["GEMINI_API_KEY"] = "a"
        self.assertEqual(config.gemini_key(), "a")

    def test_empty_values_fall_back_to_defaults(self):
        os.environ.update(REPSQUAD_DB="", REPSQUAD_HOST="", REPSQUAD_PORT="", GEMINI_MODEL="")
        self.assertEqual((config.db_path(), config.host(), config.port()), ("repsquad.db", "127.0.0.1", 8000))
        self.assertEqual(config.gemini_models()[0], "gemini-3.5-flash")

    def test_non_numeric_port_env_is_a_clear_error(self):
        os.environ["REPSQUAD_PORT"] = "abc"
        with self.assertRaisesRegex(ValueError, "REPSQUAD_PORT"):
            config.port()

    def test_ai_module_reads_config_not_environ(self):
        os.environ["GEMINI_MODEL"] = "my-model"
        self.assertEqual(ai.active_model(), "Gemini (my-model)")
        self.assertFalse(hasattr(ai, "os"))


if __name__ == "__main__":
    unittest.main()
