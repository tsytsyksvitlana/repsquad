import unittest

import run


class ParsePortTests(unittest.TestCase):
    def test_no_argument_defers_to_config(self):
        self.assertIsNone(run.parse_port([]))

    def test_numeric_argument(self):
        self.assertEqual(run.parse_port(["8123"]), 8123)

    def test_non_numeric_argument_exits_with_a_clear_message(self):
        with self.assertRaises(SystemExit) as cm:
            run.parse_port(["abc"])
        self.assertIn("Invalid port 'abc'", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
