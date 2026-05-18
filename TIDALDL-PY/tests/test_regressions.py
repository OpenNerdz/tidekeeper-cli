import sys
import unittest
from types import SimpleNamespace
from unittest import mock

import tidal_dl
from tidal_dl import apiKey, events, paths
from tidal_dl.enums import AudioQuality, Type, VideoQuality
from tidal_dl.model import StreamUrl
from tidal_dl.tidal import TidalAPI


class CliAuthPathRegressionTests(unittest.TestCase):
    def _artist(self, name="Artist"):
        return SimpleNamespace(name=name)

    def _album(self):
        artist = self._artist()
        return SimpleNamespace(
            id=123,
            artists=[artist],
            artist=artist,
            title="Album",
            releaseDate="2026-01-02",
            audioQuality="HIGH",
            audioModes=[],
            explicit=False,
            duration=180,
            numberOfTracks=1,
            numberOfVideos=0,
            numberOfVolumes=1,
            type="ALBUM",
            cover=None,
        )

    def _track(self):
        artist = self._artist()
        album = SimpleNamespace(id=123, title="Album")
        return SimpleNamespace(
            id=456,
            artists=[artist],
            artist=artist,
            album=album,
            title="Track",
            version=None,
            explicit=False,
            trackNumber=1,
            trackNumberOnPlaylist=1,
            volumeNumber=1,
            audioQuality="HIGH",
            duration=180,
        )

    def _video(self):
        artist = self._artist()
        album = self._album()
        return SimpleNamespace(
            id=789,
            artists=[artist],
            artist=artist,
            album=album,
            title="Video",
            explicit=False,
            trackNumber=1,
            releaseDate="2026-01-02",
        )

    def _playlist(self):
        return SimpleNamespace(uuid="playlist-uuid", title="Playlist")

    def _stream(self):
        stream = StreamUrl()
        stream.url = "https://example.invalid/audio.m4a"
        stream.codec = "aac"
        stream.container = "mp4"
        stream.manifestMimeType = "application/dash+xml"
        return stream

    def test_device_auth_pending_without_status_keeps_waiting(self):
        api = TidalAPI()
        api.key.deviceCode = "device-code"

        with mock.patch.object(api, "__post__", return_value={"error": "authorization_pending"}):
            self.assertFalse(api.checkAuthStatus())

    def test_link_command_aborts_when_login_fails(self):
        old_argv = sys.argv
        sys.argv = ["tidekeeper", "--link", "123456"]
        try:
            with mock.patch.object(tidal_dl.aigpy.path, "mkdirs", return_value=True), \
                 mock.patch.object(tidal_dl, "loginByConfig", return_value=False), \
                 mock.patch.object(tidal_dl, "loginByWeb", return_value=False), \
                 mock.patch.object(tidal_dl, "start") as start:
                tidal_dl.mainCommand()
        finally:
            sys.argv = old_argv

        start.assert_not_called()

    def test_empty_path_formats_use_default_formats(self):
        old_values = {
            "downloadPath": paths.SETTINGS.downloadPath,
            "albumFolderFormat": paths.SETTINGS.albumFolderFormat,
            "playlistFolderFormat": paths.SETTINGS.playlistFolderFormat,
            "trackFileFormat": paths.SETTINGS.trackFileFormat,
            "videoFileFormat": paths.SETTINGS.videoFileFormat,
            "usePlaylistFolder": paths.SETTINGS.usePlaylistFolder,
        }
        try:
            paths.SETTINGS.downloadPath = "/tmp/tidekeeper"
            paths.SETTINGS.albumFolderFormat = ""
            paths.SETTINGS.playlistFolderFormat = ""
            paths.SETTINGS.trackFileFormat = ""
            paths.SETTINGS.videoFileFormat = ""
            paths.SETTINGS.usePlaylistFolder = True

            self.assertIn("Album [123] [2026]", paths.getAlbumPath(self._album()))
            self.assertIn("Playlist [playlist-uuid]", paths.getPlaylistPath(self._playlist()))
            self.assertTrue(paths.getTrackPath(self._track(), self._stream(), self._album()).endswith("01 - Artist - Track.m4a"))
            self.assertTrue(paths.getVideoPath(self._video()).endswith("01 - Artist - Video.mp4"))
        finally:
            for key, value in old_values.items():
                setattr(paths.SETTINGS, key, value)

    def test_album_items_skip_unstreamable_tracks_instead_of_treating_them_as_videos(self):
        api = TidalAPI()
        api.__getItems__ = lambda path: [
            {"type": "track", "item": {"id": 1, "streamReady": True, "title": "Ready"}},
            {"type": "track", "item": {"id": 2, "streamReady": False, "title": "Unavailable"}},
            {"type": "video", "item": {"id": 3, "title": "Video"}},
        ]

        tracks, videos = api.getItems("album-id", Type.Album)

        self.assertEqual([track.id for track in tracks], [1])
        self.assertEqual([video.id for video in videos], [3])

    def test_manual_access_token_login_persists_userid(self):
        old_values = {
            "userid": events.TOKEN.userid,
            "countryCode": events.TOKEN.countryCode,
            "accessToken": events.TOKEN.accessToken,
            "refreshToken": events.TOKEN.refreshToken,
            "expiresAfter": events.TOKEN.expiresAfter,
        }
        try:
            events.TOKEN.userid = None
            events.TOKEN.countryCode = None
            events.TOKEN.accessToken = None
            events.TOKEN.refreshToken = "old-refresh"
            events.TOKEN.expiresAfter = 0

            def fake_login(access_token, userid=None):
                events.TIDAL_API.key.userId = "user-123"
                events.TIDAL_API.key.countryCode = "GB"
                events.TIDAL_API.key.accessToken = access_token

            with mock.patch.object(events.Printf, "enter", side_effect=["access-token", "0"]), \
                 mock.patch.object(events.TIDAL_API, "loginByAccessToken", fake_login), \
                 mock.patch.object(events.TOKEN, "save"):
                events.loginByAccessToken()

            self.assertEqual(events.TOKEN.userid, "user-123")
            self.assertEqual(events.TOKEN.countryCode, "GB")
        finally:
            for key, value in old_values.items():
                setattr(events.TOKEN, key, value)

    def test_refresh_access_token_preserves_rotated_refresh_token(self):
        api = TidalAPI()
        result = {
            "user": {"userId": "user-123", "countryCode": "GB"},
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }

        with mock.patch.object(api, "__post__", return_value=result):
            self.assertTrue(api.refreshAccessToken("old-refresh"))

        self.assertEqual(api.key.refreshToken, "new-refresh")

    def test_login_by_config_persists_rotated_refresh_token(self):
        old_values = {
            "userid": events.TOKEN.userid,
            "countryCode": events.TOKEN.countryCode,
            "accessToken": events.TOKEN.accessToken,
            "refreshToken": events.TOKEN.refreshToken,
            "expiresAfter": events.TOKEN.expiresAfter,
        }
        try:
            events.TOKEN.userid = "user-123"
            events.TOKEN.countryCode = "GB"
            events.TOKEN.accessToken = "expired-access"
            events.TOKEN.refreshToken = "old-refresh"
            events.TOKEN.expiresAfter = 0

            def fake_refresh(refresh_token):
                events.TIDAL_API.key.userId = "user-123"
                events.TIDAL_API.key.countryCode = "GB"
                events.TIDAL_API.key.accessToken = "new-access"
                events.TIDAL_API.key.refreshToken = "new-refresh"
                events.TIDAL_API.key.expiresIn = 3600
                return True

            with mock.patch.object(events.TIDAL_API, "verifyAccessToken", return_value=False), \
                 mock.patch.object(events.TIDAL_API, "refreshAccessToken", fake_refresh), \
                 mock.patch.object(events.TOKEN, "save"):
                self.assertTrue(events.loginByConfig())

            self.assertEqual(events.TOKEN.refreshToken, "new-refresh")
        finally:
            for key, value in old_values.items():
                setattr(events.TOKEN, key, value)

    def test_invalid_api_key_index_returns_error_key_dict(self):
        self.assertFalse(apiKey.isItemValid(999))
        self.assertEqual(apiKey.getItem(999)["platform"], "None")

    def test_album_flag_handles_missing_audio_modes(self):
        album = SimpleNamespace(audioQuality="LOW", audioModes=None, explicit=False)
        self.assertEqual(TidalAPI().getFlag(album, Type.Album), "")

    def test_get_cover_data_uses_timeout(self):
        response = SimpleNamespace(content=b"cover")
        with mock.patch("tidal_dl.tidal.requests.get", return_value=response) as get:
            self.assertEqual(TidalAPI().getCoverData("abc-def"), b"cover")

        self.assertEqual(get.call_args.kwargs["timeout"], (5, 60))

    def test_video_path_respects_playlist_folder_setting(self):
        old_values = {
            "downloadPath": paths.SETTINGS.downloadPath,
            "usePlaylistFolder": paths.SETTINGS.usePlaylistFolder,
            "albumFolderFormat": paths.SETTINGS.albumFolderFormat,
            "playlistFolderFormat": paths.SETTINGS.playlistFolderFormat,
            "videoFileFormat": paths.SETTINGS.videoFileFormat,
        }
        try:
            paths.SETTINGS.downloadPath = "/tmp/tidekeeper"
            paths.SETTINGS.usePlaylistFolder = False
            paths.SETTINGS.albumFolderFormat = "{AlbumTitle}"
            paths.SETTINGS.playlistFolderFormat = "Playlist/{PlaylistName}"
            paths.SETTINGS.videoFileFormat = "{VideoNumber} - {VideoTitle}"

            video_path = paths.getVideoPath(self._video(), None, self._playlist())

            self.assertTrue(video_path.startswith("/tmp/tidekeeper/Video/"))
            self.assertNotIn("Playlist/Playlist", video_path)
        finally:
            for key, value in old_values.items():
                setattr(paths.SETTINGS, key, value)


if __name__ == "__main__":
    unittest.main()
