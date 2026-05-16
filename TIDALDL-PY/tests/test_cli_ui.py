import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tidal_dl import printf
from tidal_dl.printf import Printf


class CliUiTests(unittest.TestCase):
    def test_compact_help_uses_one_option_per_line(self):
        output = io.StringIO()

        with mock.patch.object(printf, "isTermux", return_value=True):
            with redirect_stdout(output):
                Printf.usage()

        text = output.getvalue()
        self.assertIn("-l, --link URL\n  Download URL/ID/file", text)
        self.assertNotIn("OPTION                  DESCRIPTION", text)

    def test_compact_dashboard_uses_one_command_per_line(self):
        output = io.StringIO()

        with mock.patch.object(printf, "isTermux", return_value=True):
            with redirect_stdout(output):
                Printf.dashboard()

        text = output.getvalue()
        self.assertIn("1 Login / refresh", text)
        self.assertIn("5 Quality", text)
        self.assertIn("clear / cls Clear screen", text)
        self.assertNotIn("1 Login/refresh   2 Logout", text)


if __name__ == "__main__":
    unittest.main()
