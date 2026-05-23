import base64
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import tidal_dl
from tidal_dl import apiKey, download, events, paths
from tidal_dl.enums import AudioQuality, Type, VideoQuality
from tidal_dl.gui_app.backend import TidekeeperBackend
from tidal_dl.model import StreamUrl
from tidal_dl.settings import Settings
from tidal_dl.tidal import TidalAPI, TidalApiError


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
        stream.urls = [stream.url]
        stream.codec = "aac"
        stream.container = "mp4"
        stream.manifestMimeType = "application/dash+xml"
        stream.soundQuality = "HIGH"
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

    def test_doctor_command_runs_without_login_or_download(self):
        old_argv = sys.argv
        sys.argv = ["tidekeeper", "--doctor"]
        try:
            with mock.patch.object(tidal_dl, "runDoctor", return_value=True) as doctor, \
                 mock.patch.object(tidal_dl, "loginByConfig") as login, \
                 mock.patch.object(tidal_dl, "start") as start:
                tidal_dl.mainCommand()
        finally:
            sys.argv = old_argv

        doctor.assert_called_once_with()
        login.assert_not_called()
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

    def test_gui_backend_syncs_saved_country_code_before_search(self):
        old_values = {
            "userid": events.TOKEN.userid,
            "countryCode": events.TOKEN.countryCode,
            "accessToken": events.TOKEN.accessToken,
            "refreshToken": events.TOKEN.refreshToken,
            "expiresAfter": events.TOKEN.expiresAfter,
            "api_user": events.TIDAL_API.key.userId,
            "api_country": events.TIDAL_API.key.countryCode,
            "api_access": events.TIDAL_API.key.accessToken,
            "api_refresh": events.TIDAL_API.key.refreshToken,
        }
        try:
            events.TOKEN.userid = "user-123"
            events.TOKEN.countryCode = "GB"
            events.TOKEN.accessToken = "saved-access"
            events.TOKEN.refreshToken = "saved-refresh"
            events.TOKEN.expiresAfter = time.time() + 3600
            events.TIDAL_API.key.userId = None
            events.TIDAL_API.key.countryCode = None
            events.TIDAL_API.key.accessToken = None
            events.TIDAL_API.key.refreshToken = None

            backend = TidekeeperBackend()
            backend._ensure_catalog_session()

            self.assertEqual(events.TIDAL_API.key.userId, "user-123")
            self.assertEqual(events.TIDAL_API.key.countryCode, "GB")
            self.assertEqual(events.TIDAL_API.key.accessToken, "saved-access")
        finally:
            for key, value in old_values.items():
                if key.startswith("api_"):
                    attr = {
                        "api_user": "userId",
                        "api_country": "countryCode",
                        "api_access": "accessToken",
                        "api_refresh": "refreshToken",
                    }[key]
                    setattr(events.TIDAL_API.key, attr, value)
                else:
                    setattr(events.TOKEN, key, value)

    def test_gui_backend_recovers_missing_saved_country_code(self):
        old_values = {
            "userid": events.TOKEN.userid,
            "countryCode": events.TOKEN.countryCode,
            "accessToken": events.TOKEN.accessToken,
            "refreshToken": events.TOKEN.refreshToken,
            "expiresAfter": events.TOKEN.expiresAfter,
        }
        try:
            events.TOKEN.userid = "user-123"
            events.TOKEN.countryCode = None
            events.TOKEN.accessToken = "saved-access"
            events.TOKEN.refreshToken = "saved-refresh"
            events.TOKEN.expiresAfter = time.time() + 3600

            def fake_login(access_token, userid=None):
                events.TIDAL_API.key.userId = userid
                events.TIDAL_API.key.countryCode = "GB"
                events.TIDAL_API.key.accessToken = access_token
                events.TIDAL_API.key.refreshToken = events.TOKEN.refreshToken

            backend = TidekeeperBackend()
            with mock.patch.object(events.TIDAL_API, "loginByAccessToken", fake_login), \
                 mock.patch.object(events.TOKEN, "save"):
                backend._ensure_catalog_session()

            self.assertEqual(events.TOKEN.countryCode, "GB")
            self.assertEqual(events.TIDAL_API.key.countryCode, "GB")
        finally:
            for key, value in old_values.items():
                setattr(events.TOKEN, key, value)

    def test_gui_backend_artist_tracks_expands_albums_without_duplicates(self):
        artist = SimpleNamespace(id=99, name="Artist")
        album_one = SimpleNamespace(id=10, title="First")
        album_two = SimpleNamespace(id=20, title="Second")
        track_one = self._track()
        track_one.id = 1
        track_one.title = "One"
        track_two = self._track()
        track_two.id = 2
        track_two.title = "Two"

        def fake_items(album_id, etype):
            self.assertEqual(etype, Type.Album)
            if album_id == 10:
                return [track_one, track_two], []
            return [track_one], []

        backend = TidekeeperBackend()
        search_item = SimpleNamespace(source=artist, identifier="99")
        with mock.patch.object(backend, "_ensure_catalog_session"), \
             mock.patch.object(events.TIDAL_API, "getArtistAlbums", return_value=[album_one, album_one, album_two]), \
             mock.patch.object(events.TIDAL_API, "getItems", side_effect=fake_items):
            tracks = backend.artist_tracks(search_item)

        self.assertEqual([item.identifier for item in tracks], ["1", "2"])
        self.assertEqual([item.kind for item in tracks], [Type.Track, Type.Track])

    def test_gui_backend_all_search_combines_catalog_types(self):
        artist = SimpleNamespace(id=99, name="Artist")
        album = self._album()
        track = self._track()

        def fake_items(result, etype):
            return {
                Type.Artist: [artist],
                Type.Album: [album],
                Type.Track: [track],
                Type.Playlist: [],
                Type.Video: [],
            }[etype]

        backend = TidekeeperBackend()
        with mock.patch.object(backend, "_ensure_catalog_session"), \
             mock.patch.object(events.TIDAL_API, "search", return_value=object()), \
             mock.patch.object(events.TIDAL_API, "getSearchResultItems", side_effect=fake_items):
            items = backend.search("artist", Type.Null)

        self.assertEqual([item.kind for item in items], [Type.Artist, Type.Album, Type.Track])
        self.assertEqual([item.title for item in items], ["Artist", "Album", "Track"])

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

    def test_atmos_stream_adds_identifying_suffix_to_default_track_filename(self):
        old_values = {
            "downloadPath": paths.SETTINGS.downloadPath,
            "trackFileFormat": paths.SETTINGS.trackFileFormat,
            "audioQuality": paths.SETTINGS.audioQuality,
        }
        stream = self._stream()
        stream.codec = "ec-3"
        stream.soundQuality = "DOLBY_ATMOS"
        try:
            paths.SETTINGS.downloadPath = "/tmp/tidekeeper"
            paths.SETTINGS.trackFileFormat = "{TrackNumber} - {ArtistName} - {TrackTitle}{ExplicitFlag}"
            paths.SETTINGS.audioQuality = AudioQuality.Atmos

            track_path = paths.getTrackPath(self._track(), stream, self._album())

            self.assertTrue(track_path.endswith("01 - Artist - Track [Dolby Atmos].m4a"))
        finally:
            for key, value in old_values.items():
                setattr(paths.SETTINGS, key, value)

    def test_track_path_supports_stream_quality_and_codec_tokens(self):
        old_values = {
            "downloadPath": paths.SETTINGS.downloadPath,
            "trackFileFormat": paths.SETTINGS.trackFileFormat,
            "audioQuality": paths.SETTINGS.audioQuality,
        }
        stream = self._stream()
        stream.codec = "ec-3"
        stream.soundQuality = "DOLBY_ATMOS"
        try:
            paths.SETTINGS.downloadPath = "/tmp/tidekeeper"
            paths.SETTINGS.trackFileFormat = "{TrackTitle} [{StreamQuality}] [{Codec}]"
            paths.SETTINGS.audioQuality = AudioQuality.Atmos

            track_path = paths.getTrackPath(self._track(), stream, self._album())

            self.assertTrue(track_path.endswith("Track [Dolby Atmos] [ec-3].m4a"))
        finally:
            for key, value in old_values.items():
                setattr(paths.SETTINGS, key, value)

    def test_metadata_save_failure_is_reported(self):
        track = self._track()
        album = self._album()
        track.album = album
        track.copyRight = "Copyright"
        track.isrc = "ISRC"
        fake_tag = SimpleNamespace(save=mock.Mock(return_value=(False, "tag write failed")))

        with mock.patch.object(download.aigpy.tag, "TagTool", return_value=fake_tag), \
             mock.patch.object(download.TIDAL_API, "getCoverUrl", return_value=""):
            with self.assertRaisesRegex(Exception, "tag write failed"):
                download.__setMetaData__(track, album, "/tmp/track.m4a", None, "")

    def test_metadata_tags_are_created_before_save_when_missing(self):
        track = self._track()
        album = self._album()
        track.album = album
        track.copyRight = "Copyright"
        track.isrc = "ISRC"
        fake_handle = SimpleNamespace(tags=None, add_tags=mock.Mock())
        fake_tag = SimpleNamespace(_handle=fake_handle, save=mock.Mock(return_value=True))

        with mock.patch.object(download.aigpy.tag, "TagTool", return_value=fake_tag), \
             mock.patch.object(download.TIDAL_API, "getCoverUrl", return_value=""):
            download.__setMetaData__(track, album, "/tmp/track.m4a", None, "")

        fake_handle.add_tags.assert_called_once_with()
        fake_tag.save.assert_called_once_with("")

    def test_failed_track_log_is_reusable_as_link_file(self):
        old_download_path = download.SETTINGS.downloadPath
        track = self._track()
        album = self._album()
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                download.SETTINGS.downloadPath = temp_dir
                with mock.patch.object(download.TIDAL_API, "getStreamUrl", side_effect=Exception("HTTP 429")):
                    ok, msg = download.downloadTrack(track, album)

                failed_log = Path(temp_dir) / "failed-tracks.txt"
                self.assertFalse(ok)
                self.assertIn("HTTP 429", msg)
                self.assertTrue(failed_log.exists())
                lines = failed_log.read_text(encoding="utf-8").splitlines()
                retry_urls = [line for line in lines if line and not line.startswith("#")]
                self.assertEqual(retry_urls, ["https://tidal.com/browse/track/456"])
                self.assertTrue(any("Track" in line and "HTTP 429" in line for line in lines))
            finally:
                download.SETTINGS.downloadPath = old_download_path

    def test_atmos_client_not_entitled_falls_back_to_max_stream(self):
        api = TidalAPI()
        manifest = base64.b64encode(json.dumps({
            "codecs": "flac",
            "urls": ["https://example.invalid/fallback.flac"],
            "mimeType": "audio/flac",
        }).encode("utf-8")).decode("utf-8")

        with mock.patch.object(
            api,
            "__getOpenApiTrackManifest__",
            side_effect=Exception(
                'Track manifest request failed: HTTP 403 {"errors":[{"code":"CLIENT_NOT_ENTITLED"}]}'
            ),
        ), mock.patch.object(api, "__get__", return_value={
            "trackid": 456,
            "audioQuality": "HI_RES_LOSSLESS",
            "manifestMimeType": "application/vnd.tidal.bt",
            "manifest": manifest,
        }) as fallback_get:
            stream = api.getStreamUrl(456, AudioQuality.Atmos)

        self.assertEqual(stream.soundQuality, "HI_RES_LOSSLESS")
        self.assertEqual(stream.url, "https://example.invalid/fallback.flac")
        fallback_get.assert_called_once_with(
            "tracks/456/playbackinfopostpaywall",
            {"audioquality": "HI_RES_LOSSLESS", "playbackmode": "STREAM", "assetpresentation": "FULL"},
        )

    def test_blocked_max_stream_falls_back_to_legacy_hi_res_stream(self):
        api = TidalAPI()
        manifest = base64.b64encode(json.dumps({
            "codecs": "flac",
            "urls": ["https://example.invalid/hires.flac"],
            "mimeType": "audio/flac",
        }).encode("utf-8")).decode("utf-8")

        blocked = TidalApiError(
            'Get operation failed: HTTP 403 {"errors":[{"code":"CLIENT_NOT_ENTITLED"}]}',
            403,
            ["CLIENT_NOT_ENTITLED"],
        )

        with mock.patch.object(api, "__get__", side_effect=[
            blocked,
            {
                "trackid": 456,
                "audioQuality": "HI_RES",
                "manifestMimeType": "application/vnd.tidal.bt",
                "manifest": manifest,
            },
        ]) as get:
            stream = api.getStreamUrl(456, AudioQuality.Max)

        self.assertEqual(stream.soundQuality, "HI_RES")
        self.assertEqual(stream.url, "https://example.invalid/hires.flac")
        self.assertEqual(stream.requestedQuality, "Max")
        self.assertEqual(stream.fallbackQuality, "Master")
        self.assertEqual(stream.fallbackReason, "requested format is not allowed for this account or track")
        self.assertIn("CLIENT_NOT_ENTITLED", stream.fallbackError)
        self.assertEqual(
            get.call_args_list,
            [
                mock.call(
                    "tracks/456/playbackinfopostpaywall",
                    {"audioquality": "HI_RES_LOSSLESS", "playbackmode": "STREAM", "assetpresentation": "FULL"},
                ),
                mock.call(
                    "tracks/456/playbackinfopostpaywall",
                    {"audioquality": "HI_RES", "playbackmode": "STREAM", "assetpresentation": "FULL"},
                ),
            ],
        )

    def test_settings_read_parses_audio_quality_priority(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text(json.dumps({
                "audioQuality": "Atmos",
                "audioQualityPriority": ["Atmos", "High", "HiFi", "Normal"],
                "videoQuality": "P360",
            }), encoding="utf-8")

            settings = Settings()
            settings.read(str(settings_path))

        self.assertEqual(settings.audioQuality, AudioQuality.Atmos)
        self.assertEqual(settings.audioQualityPriority, [
            AudioQuality.Atmos,
            AudioQuality.High,
            AudioQuality.HiFi,
            AudioQuality.Normal,
        ])

    def test_audio_quality_priority_accepts_user_facing_aliases(self):
        settings = Settings()

        self.assertEqual(settings.getAudioQualityPriority(
            "Dolby Atmos,High (AAC 320),Lossless,Low (AAC 96)"
        ), [
            AudioQuality.Atmos,
            AudioQuality.High,
            AudioQuality.HiFi,
            AudioQuality.Normal,
        ])

    def test_settings_save_serializes_audio_quality_priority_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings = Settings()
            settings.read(str(settings_path))
            settings.audioQuality = AudioQuality.Atmos
            settings.audioQualityPriority = [AudioQuality.Atmos, AudioQuality.High, AudioQuality.HiFi]
            settings.save()

            data = json.loads(settings_path.read_text(encoding="utf-8"))

        self.assertEqual(data["audioQuality"], "Atmos")
        self.assertEqual(data["audioQualityPriority"], ["Atmos", "High", "HiFi"])

    def test_audio_quality_priority_tries_high_before_lossless(self):
        api = TidalAPI()
        manifest = base64.b64encode(json.dumps({
            "codecs": "aac",
            "urls": ["https://example.invalid/fallback.m4a"],
            "mimeType": "audio/mp4",
        }).encode("utf-8")).decode("utf-8")

        with mock.patch.object(
            api,
            "__getOpenApiTrackManifest__",
            side_effect=Exception(
                'Track manifest request failed: HTTP 403 {"errors":[{"code":"CLIENT_NOT_ENTITLED"}]}'
            ),
        ), mock.patch.object(api, "__get__", return_value={
            "trackid": 456,
            "audioQuality": "HIGH",
            "manifestMimeType": "application/vnd.tidal.bt",
            "manifest": manifest,
        }) as fallback_get:
            stream = api.getStreamUrlByPriority(456, [
                "Atmos",
                "High",
                "HiFi",
                "Normal",
            ])

        self.assertEqual(stream.soundQuality, "HIGH")
        self.assertEqual(stream.url, "https://example.invalid/fallback.m4a")
        fallback_get.assert_called_once_with(
            "tracks/456/playbackinfopostpaywall",
            {"audioquality": "HIGH", "playbackmode": "STREAM", "assetpresentation": "FULL"},
        )

    def test_audio_quality_priority_rejects_lower_actual_quality_and_keeps_trying(self):
        api = TidalAPI()
        low_manifest = base64.b64encode(json.dumps({
            "codecs": "aac",
            "urls": ["https://example.invalid/low.m4a"],
            "mimeType": "audio/mp4",
        }).encode("utf-8")).decode("utf-8")
        lossless_manifest = base64.b64encode(json.dumps({
            "codecs": "flac",
            "urls": ["https://example.invalid/lossless.flac"],
            "mimeType": "audio/flac",
        }).encode("utf-8")).decode("utf-8")

        with mock.patch.object(
            api,
            "__getOpenApiTrackManifest__",
            side_effect=Exception(
                'Track manifest request failed: HTTP 403 {"errors":[{"code":"CLIENT_NOT_ENTITLED"}]}'
            ),
        ), mock.patch.object(api, "__get__", side_effect=[
            {
                "trackid": 456,
                "audioQuality": "LOW",
                "manifestMimeType": "application/vnd.tidal.bt",
                "manifest": low_manifest,
            },
            {
                "trackid": 456,
                "audioQuality": "LOSSLESS",
                "manifestMimeType": "application/vnd.tidal.bt",
                "manifest": lossless_manifest,
            },
        ]) as fallback_get:
            stream = api.getStreamUrlByPriority(456, [
                "Atmos",
                "High",
                "Lossless",
                "Low",
            ])

        self.assertEqual(stream.soundQuality, "LOSSLESS")
        self.assertEqual(stream.url, "https://example.invalid/lossless.flac")
        self.assertEqual(stream.requestedQuality, "Dolby Atmos")
        self.assertEqual(stream.fallbackQuality, "HiFi")
        self.assertEqual(
            fallback_get.call_args_list,
            [
                mock.call(
                    "tracks/456/playbackinfopostpaywall",
                    {"audioquality": "HIGH", "playbackmode": "STREAM", "assetpresentation": "FULL"},
                ),
                mock.call(
                    "tracks/456/playbackinfopostpaywall",
                    {"audioquality": "LOSSLESS", "playbackmode": "STREAM", "assetpresentation": "FULL"},
                ),
            ],
        )

    def test_download_track_uses_configured_audio_quality_priority(self):
        old_priority = download.SETTINGS.audioQualityPriority
        old_quality = download.SETTINGS.audioQuality
        track = self._track()
        try:
            download.SETTINGS.audioQuality = AudioQuality.Atmos
            download.SETTINGS.audioQualityPriority = [AudioQuality.Atmos, AudioQuality.High]
            expected_stream = self._stream()
            with mock.patch.object(
                download.TIDAL_API,
                "getStreamUrlByPriority",
                return_value=expected_stream,
            ) as priority_get:
                stream = download.__getTrackStream__(track.id)

            self.assertIs(stream, expected_stream)
            priority_get.assert_called_once_with(track.id, [AudioQuality.Atmos, AudioQuality.High])
        finally:
            download.SETTINGS.audioQualityPriority = old_priority
            download.SETTINGS.audioQuality = old_quality

    def test_download_track_uses_single_quality_as_strict_priority(self):
        old_priority = download.SETTINGS.audioQualityPriority
        old_quality = download.SETTINGS.audioQuality
        track = self._track()
        try:
            download.SETTINGS.audioQuality = AudioQuality.HiFi
            download.SETTINGS.audioQualityPriority = []
            expected_stream = self._stream()
            with mock.patch.object(
                download.TIDAL_API,
                "getStreamUrlByPriority",
                return_value=expected_stream,
            ) as priority_get, mock.patch.object(download.TIDAL_API, "getStreamUrl") as ladder_get:
                stream = download.__getTrackStream__(track.id)

            self.assertIs(stream, expected_stream)
            priority_get.assert_called_once_with(track.id, [AudioQuality.HiFi])
            ladder_get.assert_not_called()
        finally:
            download.SETTINGS.audioQualityPriority = old_priority
            download.SETTINGS.audioQuality = old_quality

    def test_quality_priority_command_sets_fallback_order(self):
        old_argv = sys.argv
        old_quality = tidal_dl.SETTINGS.audioQuality
        old_priority = tidal_dl.SETTINGS.audioQualityPriority
        sys.argv = ["tidekeeper", "--quality-priority", "Atmos,High,HiFi,Normal"]
        try:
            with mock.patch.object(tidal_dl.aigpy.path, "mkdirs", return_value=True), \
                 mock.patch.object(tidal_dl.SETTINGS, "save") as save:
                tidal_dl.mainCommand()

            self.assertEqual(tidal_dl.SETTINGS.audioQuality, AudioQuality.Atmos)
            self.assertEqual(tidal_dl.SETTINGS.audioQualityPriority, [
                AudioQuality.Atmos,
                AudioQuality.High,
                AudioQuality.HiFi,
                AudioQuality.Normal,
            ])
            save.assert_called()
        finally:
            sys.argv = old_argv
            tidal_dl.SETTINGS.audioQuality = old_quality
            tidal_dl.SETTINGS.audioQualityPriority = old_priority

    def test_quality_command_clears_fallback_order(self):
        old_argv = sys.argv
        old_quality = tidal_dl.SETTINGS.audioQuality
        old_priority = tidal_dl.SETTINGS.audioQualityPriority
        sys.argv = ["tidekeeper", "--quality", "High"]
        try:
            tidal_dl.SETTINGS.audioQualityPriority = [AudioQuality.Atmos, AudioQuality.High]
            with mock.patch.object(tidal_dl.aigpy.path, "mkdirs", return_value=True), \
                 mock.patch.object(tidal_dl.SETTINGS, "save"):
                tidal_dl.mainCommand()

            self.assertEqual(tidal_dl.SETTINGS.audioQuality, AudioQuality.High)
            self.assertEqual(tidal_dl.SETTINGS.audioQualityPriority, [])
        finally:
            sys.argv = old_argv
            tidal_dl.SETTINGS.audioQuality = old_quality
            tidal_dl.SETTINGS.audioQualityPriority = old_priority

    def test_tidal_url_parser_ignores_query_strings_and_fragments(self):
        api = TidalAPI()

        etype, sid = api.parseUrl("https://tidal.com/browse/track/70973230?u=1#play")

        self.assertEqual(etype, Type.Track)
        self.assertEqual(sid, "70973230")

    def test_tidal_url_parser_handles_nested_paths(self):
        api = TidalAPI()

        etype, sid = api.parseUrl("https://tidal.com/browse/album/123/track/456")

        self.assertEqual(etype, Type.Track)
        self.assertEqual(sid, "456")

    @unittest.skipIf(sys.platform.startswith("win"), "POSIX file mode check")
    def test_token_save_restricts_file_permissions(self):
        token = events.TokenSettings()
        token.accessToken = "access"
        token.refreshToken = "refresh"
        with tempfile.TemporaryDirectory() as temp_dir:
            token.read(str(Path(temp_dir) / "token.json"))
            token.save()

            mode = Path(token._path_).stat().st_mode & 0o777

        self.assertEqual(mode, 0o600)


if __name__ == "__main__":
    unittest.main()
