import unittest

from tidal_dl.model import StreamUrl
from tidal_dl.paths import __getExtension__


class PathTests(unittest.TestCase):
    def test_dash_flac_in_mp4_container_uses_m4a_extension(self):
        stream = StreamUrl()
        stream.url = "https://example.invalid/init.mp4"
        stream.codec = "flac"
        stream.manifestMimeType = "application/dash+xml"
        stream.container = "mp4"

        self.assertEqual(__getExtension__(stream), ".m4a")

    def test_native_flac_url_uses_flac_extension(self):
        stream = StreamUrl()
        stream.url = "https://example.invalid/audio.flac"
        stream.codec = "flac"

        self.assertEqual(__getExtension__(stream), ".flac")


if __name__ == "__main__":
    unittest.main()
