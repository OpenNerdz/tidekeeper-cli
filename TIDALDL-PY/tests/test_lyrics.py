import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tidal_dl import download
from tidal_dl.model import Lyrics
from tidal_dl.tidal import TidalAPI


class LyricsTests(unittest.TestCase):
    def test_timed_subtitles_write_lrc_and_plain_lyrics_tag_metadata(self):
        data = SimpleNamespace(subtitles="[00:01.00]Timed lyric", lyrics="Plain lyric")

        metadata, file_text, extension = download.__lyricsPayload__(data)

        self.assertEqual(metadata, "Plain lyric")
        self.assertEqual(file_text, "[00:01.00]Timed lyric")
        self.assertEqual(extension, ".lrc")

    def test_plain_lyrics_fall_back_to_txt_sidecar(self):
        data = SimpleNamespace(subtitles=None, lyrics="Plain lyric")
        old_setting = download.SETTINGS.lyricFile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / "track.flac"
            media_path.write_bytes(b"audio")

            try:
                download.SETTINGS.lyricFile = True
                metadata = download.__writeLyricsFile__(str(media_path), data)
            finally:
                download.SETTINGS.lyricFile = old_setting

            self.assertEqual(metadata, "Plain lyric")
            self.assertEqual((Path(temp_dir) / "track.txt").read_text(), "Plain lyric")
            self.assertFalse((Path(temp_dir) / "track.lrc").exists())

    def test_lyrics_sidecar_is_written_as_utf8(self):
        data = SimpleNamespace(subtitles="[00:01.00]Can’t stop", lyrics="Can’t stop")
        old_setting = download.SETTINGS.lyricFile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / "track.m4a"
            media_path.write_bytes(b"audio")

            try:
                download.SETTINGS.lyricFile = True
                metadata = download.__writeLyricsFile__(str(media_path), data)
            finally:
                download.SETTINGS.lyricFile = old_setting

            self.assertEqual(metadata, "Can’t stop")
            self.assertEqual((Path(temp_dir) / "track.lrc").read_bytes(), "[00:01.00]Can’t stop".encode("utf-8"))

    def test_timed_lyrics_fallback_uses_matching_track_version(self):
        old_setting = download.SETTINGS.lyricFile
        artist = SimpleNamespace(name="Ariana Grande")
        track = SimpleNamespace(id=1, title="Song", artists=[artist])
        candidate = SimpleNamespace(id=2, title="Song", artists=[artist])
        primary = Lyrics()
        primary.trackId = 1
        primary.lyrics = "Plain lyric"
        fallback = Lyrics()
        fallback.trackId = 2
        fallback.lyrics = "Fallback plain"
        fallback.subtitles = "[00:01.00]Timed lyric"

        try:
            download.SETTINGS.lyricFile = True
            with mock.patch.object(download.TIDAL_API, "getLyrics", side_effect=[primary, fallback]) as get_lyrics, \
                 mock.patch.object(download.TIDAL_API, "search", return_value=object()) as search, \
                 mock.patch.object(download.TIDAL_API, "getSearchResultItems", return_value=[candidate]):
                lyrics = download.__getLyricsForTrack__(track)
        finally:
            download.SETTINGS.lyricFile = old_setting

        self.assertEqual(lyrics.lyrics, "Plain lyric")
        self.assertEqual(lyrics.subtitles, "[00:01.00]Timed lyric")
        self.assertEqual([call.args[0] for call in get_lyrics.call_args_list], [1, 2])
        search.assert_called()

    def test_empty_lyrics_do_not_create_sidecar(self):
        data = SimpleNamespace(subtitles=" ", lyrics="")
        old_setting = download.SETTINGS.lyricFile

        with tempfile.TemporaryDirectory() as temp_dir:
            media_path = Path(temp_dir) / "track.flac"
            media_path.write_bytes(b"audio")

            try:
                download.SETTINGS.lyricFile = True
                metadata = download.__writeLyricsFile__(str(media_path), data)
            finally:
                download.SETTINGS.lyricFile = old_setting

            self.assertEqual(metadata, "")
            self.assertFalse((Path(temp_dir) / "track.txt").exists())
            self.assertFalse((Path(temp_dir) / "track.lrc").exists())

    def test_get_lyrics_uses_current_api_host(self):
        api = TidalAPI()

        with mock.patch.object(api, "__get__", return_value={"trackId": 42298, "lyrics": "Plain lyric"}) as get:
            lyrics = api.getLyrics(42298)

        self.assertIsInstance(lyrics, Lyrics)
        self.assertEqual(lyrics.lyrics, "Plain lyric")
        get.assert_called_once_with("tracks/42298/lyrics", urlpre="https://api.tidal.com/v1/")


if __name__ == "__main__":
    unittest.main()
