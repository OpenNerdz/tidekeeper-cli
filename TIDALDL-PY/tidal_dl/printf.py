#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   printf.py
@Time    :   2020/08/16
@Author  :   Yaronzz
@Version :   3.0
@Contact :   yaronhuang@foxmail.com
@Desc    :
'''
import threading
import aigpy
import logging
import prettytable
import re
import shutil

from . import apiKey as apiKey

from .model import *
from .paths import *
from .settings import *
from .lang.language import *


VERSION = '2026.5.16.5'
PROJECT_URL = 'https://github.com/OpenNerdz/tidekeeper-cli'
MIN_UI_WIDTH = 78
MAX_UI_WIDTH = 96
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

print_mutex = threading.Lock()


class Printf(object):

    @staticmethod
    def logo():
        text = f"Tidekeeper CLI {VERSION}\n{PROJECT_URL}"
        print(text)
        logging.info(text)

    @staticmethod
    def __onOff__(value):
        return "on" if value else "off"

    @staticmethod
    def __status__(value):
        return aigpy.cmd.green("on") if value else aigpy.cmd.yellow("off")

    @staticmethod
    def __enumName__(value):
        text = str(value)
        return text.rsplit(".", 1)[-1]

    @staticmethod
    def __width__():
        width = shutil.get_terminal_size((MAX_UI_WIDTH, 20)).columns
        return max(MIN_UI_WIDTH, min(width, MAX_UI_WIDTH))

    @staticmethod
    def __fit__(text, width):
        text = str(text)
        visible = Printf.__visibleLen__(text)
        if visible <= width:
            return text
        text = ANSI_RE.sub("", text)
        if width <= 3:
            return text[:width]
        return text[:width - 3] + "..."

    @staticmethod
    def __visibleLen__(text):
        return len(ANSI_RE.sub("", str(text)))

    @staticmethod
    def __padRight__(text, width):
        text = str(text)
        return text + (" " * max(width - Printf.__visibleLen__(text), 0))

    @staticmethod
    def __boxTop__(title, width):
        title = f" {title} "
        remaining = max(width - len(title) - 2, 0)
        return "+" + title + ("-" * remaining) + "+"

    @staticmethod
    def __boxBottom__(width):
        return "+" + ("-" * (width - 2)) + "+"

    @staticmethod
    def __boxLine__(left, right="", width=None):
        width = width or Printf.__width__()
        content_width = width - 4
        if right:
            gap = content_width - Printf.__visibleLen__(left) - Printf.__visibleLen__(right)
            if gap < 2:
                left = Printf.__fit__(left, content_width - Printf.__visibleLen__(right) - 2)
                gap = content_width - Printf.__visibleLen__(left) - Printf.__visibleLen__(right)
            text = left + (" " * gap) + right
        else:
            text = Printf.__fit__(left, content_width)
        return "| " + Printf.__padRight__(text, content_width) + " |"

    @staticmethod
    def __boxEmpty__(width):
        return Printf.__boxLine__("", width=width)

    @staticmethod
    def __printBox__(title, rows):
        width = Printf.__width__()
        print(Printf.__boxTop__(title, width))
        for row in rows:
            if row is None:
                print(Printf.__boxEmpty__(width))
            elif isinstance(row, tuple):
                print(Printf.__boxLine__(row[0], row[1], width))
            else:
                print(Printf.__boxLine__(row, width=width))
        print(Printf.__boxBottom__(width))

    @staticmethod
    def __gettable__(columns, rows):
        tb = prettytable.PrettyTable()
        tb.field_names = list(aigpy.cmd.green(item) for item in columns)
        tb.align = 'l'
        for item in rows:
            tb.add_row(item)
        return tb

    @staticmethod
    def usage():
        Printf.logo()
        print("")
        tb = Printf.__gettable__(["OPTION", "DESCRIPTION"], [
            ["-h, --help", "Show this help"],
            ["-v, --version", "Show version"],
            ["-g, --gui", "Open the simple GUI"],
            ["-l, --link", "Download a Tidal URL, ID, or text file"],
            ["-o, --output", "Set download path"],
            ["-q, --quality", "Set audio quality: Normal, High, HiFi, Master, Max"],
            ["-r, --resolution", "Set video quality: P1080, P720, P480, P360"]
        ])
        tb.set_style(prettytable.PLAIN_COLUMNS)
        print(tb)

    @staticmethod
    def checkVersion():
        onlineVer = aigpy.pip.getLastVersion('tidekeeper-cli')
        if onlineVer is not None:
            icmp = aigpy.system.cmpVersion(onlineVer, VERSION)
            if icmp > 0:
                Printf.info(LANG.select.PRINT_LATEST_VERSION + ' ' + onlineVer)

    @staticmethod
    def settings():
        data = SETTINGS
        tb = Printf.__gettable__([LANG.select.SETTING, LANG.select.VALUE], [
            #settings - path and format
            [LANG.select.SETTING_PATH, getProfilePath()],
            [LANG.select.SETTING_DOWNLOAD_PATH, data.downloadPath],
            [LANG.select.SETTING_ALBUM_FOLDER_FORMAT, data.albumFolderFormat],
            [LANG.select.SETTING_PLAYLIST_FOLDER_FORMAT, data.playlistFolderFormat],
            [LANG.select.SETTING_TRACK_FILE_FORMAT, data.trackFileFormat],
            [LANG.select.SETTING_VIDEO_FILE_FORMAT, data.videoFileFormat],

            #settings - quality
            [LANG.select.SETTING_AUDIO_QUALITY, data.audioQuality],
            [LANG.select.SETTING_VIDEO_QUALITY, data.videoQuality],

            #settings - else
            [LANG.select.SETTING_USE_PLAYLIST_FOLDER, data.usePlaylistFolder],
            [LANG.select.SETTING_CHECK_EXIST, data.checkExist],
            [LANG.select.SETTING_SHOW_PROGRESS, data.showProgress],
            [LANG.select.SETTING_SHOW_TRACKINFO, data.showTrackInfo],
            [LANG.select.SETTING_SAVE_ALBUMINFO, data.saveAlbumInfo],
            [LANG.select.SETTING_DOWNLOAD_VIDEOS, data.downloadVideos],
            [LANG.select.SETTING_SAVE_COVERS, data.saveCovers],
            [LANG.select.SETTING_INCLUDE_EP, data.includeEP],
            [LANG.select.SETTING_LANGUAGE, LANG.getLangName(data.language)],
            [LANG.select.SETTING_ADD_LRC_FILE, data.lyricFile],
            [LANG.select.SETTING_MULITHREAD_DOWNLOAD, data.multiThread],
            [LANG.select.SETTING_APIKEY, f"[{data.apiKeyIndex}]" + apiKey.getItem(data.apiKeyIndex)['formats']],
            [LANG.select.SETTING_DOWNLOAD_DELAY, data.downloadDelay],
        ])
        print(tb)

    @staticmethod
    def dashboard():
        data = SETTINGS
        signed_in = not aigpy.string.isNull(TOKEN.accessToken)
        account = aigpy.cmd.green("signed in") if signed_in else aigpy.cmd.yellow("not signed in")
        api_key = apiKey.getItem(data.apiKeyIndex)

        print("")
        Printf.__printBox__("Tidekeeper CLI", [
            (aigpy.cmd.green(f"v{VERSION}"), PROJECT_URL),
            None,
            ("Account", f"{account}  region {TOKEN.countryCode or 'unknown'}"),
            ("Downloads", data.downloadPath),
        ])
        Printf.__printBox__("Session", [
            ("Audio", Printf.__enumName__(data.audioQuality)),
            ("Video", Printf.__enumName__(data.videoQuality)),
            ("Client", f"[{data.apiKeyIndex}] {api_key['platform']} - {api_key['formats']}"),
            (
                "Flags",
                "progress {}   multithread {}   covers {}".format(
                    Printf.__status__(data.showProgress),
                    Printf.__status__(data.multiThread),
                    Printf.__status__(data.saveCovers),
                ),
            ),
        ])
        Printf.__printBox__("Commands", [
            ("Download", "paste URL, ID, or .txt file path"),
            ("Account", "login | logout | token"),
            ("Library", "path | quality | settings | client"),
            ("Inspect", "show | help | exit"),
            ("Shortcuts", "1 login | 4 path | 5 quality | 6 settings | 0 exit"),
        ])
        print("")

    @staticmethod
    def choices():
        Printf.dashboard()

    @staticmethod
    def enter(string):
        aigpy.cmd.colorPrint(string, aigpy.cmd.TextColor.Yellow, None)
        ret = input("")
        return ret

    @staticmethod
    def enterBool(string):
        aigpy.cmd.colorPrint(string, aigpy.cmd.TextColor.Yellow, None)
        ret = input("")
        return ret == '1'

    @staticmethod
    def enterPath(string, errmsg, retWord='0', default=""):
        while True:
            ret = aigpy.cmd.inputPath(aigpy.cmd.yellow(string), retWord)
            if ret == retWord:
                return default
            elif ret == "":
                print(aigpy.cmd.red(LANG.select.PRINT_ERR + " ") + errmsg)
            else:
                break
        return ret

    @staticmethod
    def enterLimit(string, errmsg, limit=[]):
        while True:
            ret = aigpy.cmd.inputLimit(aigpy.cmd.yellow(string), limit)
            if ret is None:
                print(aigpy.cmd.red(LANG.select.PRINT_ERR + " ") + errmsg)
            else:
                break
        return ret

    @staticmethod
    def enterFormat(string, current, default):
        ret = Printf.enter(string)
        if ret == '0' or aigpy.string.isNull(ret):
            return current
        if ret.lower() == 'default':
            return default
        return ret

    @staticmethod
    def err(string):
        global print_mutex
        print_mutex.acquire()
        print(aigpy.cmd.red(LANG.select.PRINT_ERR + " ") + string)
        # logging.error(string)
        print_mutex.release()

    @staticmethod
    def info(string):
        global print_mutex
        print_mutex.acquire()
        print(aigpy.cmd.blue(LANG.select.PRINT_INFO + " ") + string)
        print_mutex.release()

    @staticmethod
    def success(string):
        global print_mutex
        print_mutex.acquire()
        print(aigpy.cmd.green(LANG.select.PRINT_SUCCESS + " ") + string)
        print_mutex.release()

    @staticmethod
    def album(data: Album):
        tb = Printf.__gettable__([LANG.select.MODEL_ALBUM_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_TITLE, data.title],
            ["ID", data.id],
            [LANG.select.MODEL_TRACK_NUMBER, data.numberOfTracks],
            [LANG.select.MODEL_VIDEO_NUMBER, data.numberOfVideos],
            [LANG.select.MODEL_RELEASE_DATE, data.releaseDate],
            [LANG.select.MODEL_VERSION, data.version],
            [LANG.select.MODEL_EXPLICIT, data.explicit],
        ])
        print(tb)
        logging.info("====album " + str(data.id) + "====\n" +
                     "title:" + data.title + "\n" +
                     "track num:" + str(data.numberOfTracks) + "\n" +
                     "video num:" + str(data.numberOfVideos) + "\n" +
                     "==================================")

    @staticmethod
    def track(data: Track, stream: StreamUrl = None):
        tb = Printf.__gettable__([LANG.select.MODEL_TRACK_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_TITLE, data.title],
            ["ID", data.id],
            [LANG.select.MODEL_ALBUM, data.album.title],
            [LANG.select.MODEL_VERSION, data.version],
            [LANG.select.MODEL_EXPLICIT, data.explicit],
            ["Max-Q", data.audioQuality],
        ])
        if stream is not None:
            tb.add_row(["Get-Q", str(stream.soundQuality)])
            tb.add_row(["Get-Codec", str(stream.codec)])
        print(tb)
        logging.info("====track " + str(data.id) + "====\n" + \
                     "title:" + data.title + "\n" + \
                     "version:" + str(data.version) + "\n" + \
                     "==================================")

    @staticmethod
    def video(data: Video, stream: VideoStreamUrl = None):
        tb = Printf.__gettable__([LANG.select.MODEL_VIDEO_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_TITLE, data.title],
            [LANG.select.MODEL_ALBUM, data.album.title if data.album != None else None],
            [LANG.select.MODEL_VERSION, data.version],
            [LANG.select.MODEL_EXPLICIT, data.explicit],
            ["Max-Q", data.quality],
        ])
        if stream is not None:
            tb.add_row(["Get-Q", str(stream.resolution)])
            tb.add_row(["Get-Codec", str(stream.codec)])
        print(tb)
        logging.info("====video " + str(data.id) + "====\n" +
                     "title:" + data.title + "\n" +
                     "version:" + str(data.version) + "\n" +
                     "==================================")

    @staticmethod
    def artist(data: Artist, num):
        tb = Printf.__gettable__([LANG.select.MODEL_ARTIST_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_ID, data.id],
            [LANG.select.MODEL_NAME, data.name],
            ["Number of albums", num],
            [LANG.select.MODEL_TYPE, str(data.type)],
        ])
        print(tb)
        logging.info("====artist " + str(data.id) + "====\n" +
                     "name:" + data.name + "\n" +
                     "album num:" + str(num) + "\n" +
                     "==================================")

    @staticmethod
    def playlist(data):
        tb = Printf.__gettable__([LANG.select.MODEL_PLAYLIST_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_TITLE, data.title],
            [LANG.select.MODEL_TRACK_NUMBER, data.numberOfTracks],
            [LANG.select.MODEL_VIDEO_NUMBER, data.numberOfVideos],
        ])
        print(tb)
        logging.info("====playlist " + str(data.uuid) + "====\n" +
                     "title:" + data.title + "\n" +
                     "track num:" + str(data.numberOfTracks) + "\n" +
                     "video num:" + str(data.numberOfVideos) + "\n" +
                     "==================================")

    @staticmethod
    def mix(data):
        tb = Printf.__gettable__([LANG.select.MODEL_PLAYLIST_PROPERTY, LANG.select.VALUE], [
            [LANG.select.MODEL_ID, data.id],
            [LANG.select.MODEL_TRACK_NUMBER, len(data.tracks)],
            [LANG.select.MODEL_VIDEO_NUMBER, len(data.videos)],
        ])
        print(tb)
        logging.info("====Mix " + str(data.id) + "====\n" +
                     "track num:" + str(len(data.tracks)) + "\n" +
                     "video num:" + str(len(data.videos)) + "\n" +
                     "==================================")

    @staticmethod
    def apikeys(items):
        print("-------------API-KEYS---------------")
        tb = prettytable.PrettyTable()
        tb.field_names = [aigpy.cmd.green('Index'),
                          aigpy.cmd.green('Valid'),
                          aigpy.cmd.green('Platform'),
                          aigpy.cmd.green('Formats'), ]
        tb.align = 'l'

        for index, item in enumerate(items):
            tb.add_row([str(index),
                        aigpy.cmd.green('True') if item["valid"] == "True" else aigpy.cmd.red('False'),
                        item["platform"],
                        item["formats"]])
        print(tb)
