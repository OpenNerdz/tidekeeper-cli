import base64
import unittest
from unittest import mock

from tidal_dl.enums import AudioQuality
from tidal_dl.tidal import TidalAPI


ATMOS_MPD = """<?xml version='1.0' encoding='UTF-8'?>
<MPD xmlns="urn:mpeg:dash:schema:mpd:2011">
  <Period>
    <AdaptationSet contentType="audio">
      <Representation codecs="ec-3">
        <SegmentTemplate
          initialization="https://audio.example/init.mp4"
          media="https://audio.example/$Number$.mp4"
          startNumber="1">
          <SegmentTimeline>
            <S d="48000" r="1" />
          </SegmentTimeline>
        </SegmentTemplate>
      </Representation>
    </AdaptationSet>
  </Period>
</MPD>
"""


def data_uri(xml):
    encoded = base64.b64encode(xml.encode("utf-8")).decode("ascii")
    return f"data:application/dash+xml;base64,{encoded}"


class AtmosTests(unittest.TestCase):
    def test_atmos_quality_uses_openapi_eac3_manifest(self):
        api = TidalAPI()

        with mock.patch.object(
            api,
            "__getOpenApiTrackManifest__",
            return_value={"formats": ["EAC3_JOC"], "uri": data_uri(ATMOS_MPD)},
        ):
            stream = api.getStreamUrl(409406350, AudioQuality.Atmos)

        self.assertEqual(stream.soundQuality, "DOLBY_ATMOS")
        self.assertEqual(stream.codec, "ec-3")
        self.assertEqual(stream.manifestMimeType, "application/dash+xml")
        self.assertEqual(stream.container, "mp4")
        self.assertEqual(stream.urls, [
            "https://audio.example/init.mp4",
            "https://audio.example/1.mp4",
            "https://audio.example/2.mp4",
        ])

    def test_atmos_quality_rejects_non_atmos_manifest(self):
        api = TidalAPI()

        with mock.patch.object(
            api,
            "__getOpenApiTrackManifest__",
            return_value={"formats": ["AACLC"], "uri": data_uri(ATMOS_MPD)},
        ):
            with self.assertRaisesRegex(Exception, "Dolby Atmos stream is not available"):
                api.getStreamUrl(560060, AudioQuality.Atmos)


if __name__ == "__main__":
    unittest.main()
