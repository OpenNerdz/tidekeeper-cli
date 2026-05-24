import functools
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from tidal_dl import download


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class DownloadBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.source.mkdir()
        handler = functools.partial(QuietHandler, directory=str(self.source))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp_dir.cleanup()

    def test_single_url_download(self):
        source_file = self.source / "track.bin"
        source_file.write_bytes(b"track-bytes" * 2048)
        output_file = self.root / "track.out"

        ok, msg = download.__downloadUrls__([f"{self.base_url}/track.bin"], str(output_file), threadNum=1)

        self.assertTrue(ok, msg)
        self.assertEqual(output_file.read_bytes(), source_file.read_bytes())

    def test_multi_url_download_preserves_order(self):
        (self.source / "000.bin").write_bytes(b"first-")
        (self.source / "001.bin").write_bytes(b"second-")
        (self.source / "002.bin").write_bytes(b"third")
        output_file = self.root / "joined.out"

        ok, msg = download.__downloadUrls__([
            f"{self.base_url}/000.bin",
            f"{self.base_url}/001.bin",
            f"{self.base_url}/002.bin",
        ], str(output_file), threadNum=3)

        self.assertTrue(ok, msg)
        self.assertEqual(output_file.read_bytes(), b"first-second-third")

    def test_multi_url_sequential_download_preserves_order(self):
        (self.source / "000.bin").write_bytes(b"init")
        (self.source / "001.bin").write_bytes(b"media-one")
        (self.source / "002.bin").write_bytes(b"media-two")
        output_file = self.root / "joined-sequential.out"

        ok, msg = download.__downloadUrls__([
            f"{self.base_url}/000.bin",
            f"{self.base_url}/001.bin",
            f"{self.base_url}/002.bin",
        ], str(output_file), threadNum=1)

        self.assertTrue(ok, msg)
        self.assertEqual(output_file.read_bytes(), b"initmedia-onemedia-two")

    def test_failed_download_preserves_existing_output_file(self):
        output_file = self.root / "existing.out"
        output_file.write_bytes(b"known-good")

        ok, msg = download.__downloadUrls__([f"{self.base_url}/missing.bin"], str(output_file), threadNum=1)

        self.assertFalse(ok)
        self.assertIn("404", msg)
        self.assertEqual(output_file.read_bytes(), b"known-good")

    def test_single_url_download_resumes_existing_partial_file(self):
        output_file = self.root / "resumed.out"
        partial_file = Path(str(output_file) + ".download")
        partial_file.write_bytes(b"first-")

        class FakeResponse:
            status_code = 206
            headers = {"Content-Range": "bytes 6-11/12"}

            def iter_content(self, chunk_size):
                yield b"second"

            def close(self):
                pass

        with mock.patch.object(download, "__httpRequest__", return_value=FakeResponse()) as request:
            ok, msg = download.__downloadUrls__(
                ["https://example.invalid/media.bin"],
                str(output_file),
                threadNum=1,
                probeSize=False,
            )

        self.assertTrue(ok, msg)
        self.assertEqual(output_file.read_bytes(), b"first-second")
        self.assertFalse(partial_file.exists())
        self.assertEqual(request.call_args.kwargs["headers"], {"Range": "bytes=6-"})


if __name__ == "__main__":
    unittest.main()
