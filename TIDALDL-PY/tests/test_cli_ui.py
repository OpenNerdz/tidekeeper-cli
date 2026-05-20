import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
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
        self.assertIn("--doctor\n  Check config, auth, and local tools", text)
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

    def test_compact_api_key_picker_uses_simple_lines(self):
        items = [
            {"valid": "False", "platform": "Old", "formats": "Normal/High"},
            {"valid": "True", "platform": "Tidekeeper OAuth", "formats": "Normal/High/HiFi/Master"},
        ]
        output = io.StringIO()

        with mock.patch.object(printf, "isTermux", return_value=True):
            with redirect_stdout(output):
                Printf.apikeys(items)

        text = output.getvalue()
        self.assertIn("Tidal clients", text)
        self.assertIn("0 old - Old", text)
        self.assertIn("1 OK - Tidekeeper OAuth", text)
        self.assertNotIn("+", text)

    def test_track_output_shows_quality_fallback(self):
        output = io.StringIO()
        track = SimpleNamespace(
            title="Track",
            id=456,
            album=SimpleNamespace(title="Album"),
            version=None,
            explicit=False,
            audioQuality="DOLBY_ATMOS",
        )
        stream = SimpleNamespace(
            soundQuality="HI_RES_LOSSLESS",
            codec="flac",
            requestedQuality="Dolby Atmos",
            fallbackQuality="Max",
            fallbackReason="requested format is unavailable",
            fallbackError="Dolby Atmos stream is not available for this track.",
        )

        with redirect_stdout(output):
            Printf.track(track, stream)

        text = output.getvalue()
        self.assertIn("Requested-Q", text)
        self.assertIn("Dolby Atmos", text)
        self.assertIn("Fallback", text)
        self.assertIn("Max (requested format is unavailable)", text)


if __name__ == "__main__":
    unittest.main()
