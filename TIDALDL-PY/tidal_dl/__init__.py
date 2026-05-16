#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   __init__.py
@Time    :   2020/11/08
@Author  :   Yaronzz
@Version :   3.0
@Contact :   yaronhuang@foxmail.com
@Desc    :
'''
import sys
import getopt
import aigpy

from .events import *
from .settings import *
from .gui import startGui
from .printf import Printf


def mainCommand():
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hvgl:o:q:r:",
                                   ["help", "version", "gui", "link=", "output=", "quality=", "resolution="])
    except getopt.GetoptError as errmsg:
        Printf.err(vars(errmsg)['msg'] + ". Use 'tidal-dl -h' for usage.")
        return

    link = None
    showGui = False

    for opt, val in opts:
        if opt in ('-h', '--help'):
            Printf.usage()
            return
        if opt in ('-v', '--version'):
            Printf.logo()
            return
        if opt in ('-g', '--gui'):
            showGui = True
            continue
        if opt in ('-l', '--link'):
            link = val
            continue
        if opt in ('-o', '--output'):
            SETTINGS.downloadPath = val
            SETTINGS.save()
            continue
        if opt in ('-q', '--quality'):
            SETTINGS.audioQuality = SETTINGS.getAudioQuality(val)
            SETTINGS.save()
            continue
        if opt in ('-r', '--resolution'):
            SETTINGS.videoQuality = SETTINGS.getVideoQuality(val)
            SETTINGS.save()
            continue

    if not aigpy.path.mkdirs(SETTINGS.downloadPath):
        Printf.err(LANG.select.MSG_PATH_ERR + SETTINGS.downloadPath)
        return

    if showGui:
        startGui()
        return

    if link is not None:
        if not loginByConfig():
            loginByWeb()
        Printf.info(LANG.select.SETTING_DOWNLOAD_PATH + ':' + SETTINGS.downloadPath)
        start(link)


def normalizeChoice(choice):
    aliases = {
        "": "",
        "q": "0",
        "quit": "0",
        "exit": "0",
        "login": "1",
        "signin": "1",
        "sign-in": "1",
        "refresh": "1",
        "logout": "2",
        "signout": "2",
        "sign-out": "2",
        "token": "3",
        "access-token": "3",
        "path": "4",
        "paths": "4",
        "folder": "4",
        "quality": "5",
        "options": "6",
        "settings": "6",
        "client": "7",
        "apikey": "7",
        "api-key": "7",
        "show": "8",
        "status": "8",
        "help": "8",
        "all": "8",
        "clear": "clear",
        "cls": "clear",
    }
    clean = choice.strip()
    return aliases.get(clean.lower(), clean)


def main():
    SETTINGS.read(getProfilePath())
    TOKEN.read(getTokenPath())
    if not apiKey.isItemValid(SETTINGS.apiKeyIndex):
        SETTINGS.apiKeyIndex = apiKey.getDefaultIndex()
        SETTINGS.save()
    TIDAL_API.apiKey = apiKey.getItem(SETTINGS.apiKeyIndex)

    if len(sys.argv) > 1:
        mainCommand()
        return

    if not loginByConfig():
        loginByWeb()

    Printf.checkVersion()

    while True:
        Printf.choices()
        choice = normalizeChoice(Printf.enter("Paste URL or choice > "))
        if choice == "":
            continue
        if choice == "clear":
            Printf.clearScreen()
            continue
        if choice == "0":
            return
        elif choice == "1":
            if not loginByConfig():
                loginByWeb()
        elif choice == "2":
            logout()
        elif choice == "3":
            loginByAccessToken()
        elif choice == "4":
            changePathSettings()
        elif choice == "5":
            changeQualitySettings()
        elif choice == "6":
            changeSettings()
        elif choice == "7":
            if changeApiKey():
                loginByWeb()
        elif choice == "8":
            Printf.settings()
        else:
            start(choice)


def test():
    SETTINGS.read(getProfilePath())
    TOKEN.read(getTokenPath())

    if not loginByConfig():
        loginByWeb()

    SETTINGS.audioQuality = AudioQuality.Master
    SETTINGS.videoFileFormat = VideoQuality.P240
    SETTINGS.checkExist = False
    SETTINGS.includeEP = True
    SETTINGS.saveCovers = True
    SETTINGS.lyricFile = True
    SETTINGS.showProgress = True
    SETTINGS.showTrackInfo = True
    SETTINGS.saveAlbumInfo = True
    SETTINGS.downloadVideos = True
    SETTINGS.downloadPath = "./download/"
    SETTINGS.usePlaylistFolder = True
    SETTINGS.albumFolderFormat = R"{ArtistName}/{Flag} {AlbumTitle} [{AlbumID}] [{AlbumYear}]"
    SETTINGS.playlistFolderFormat = R"Playlist/{PlaylistName} [{PlaylistUUID}]"
    SETTINGS.trackFileFormat = R"{TrackNumber} - {ArtistName} - {TrackTitle}{ExplicitFlag}"
    SETTINGS.videoFileFormat = R"{VideoNumber} - {ArtistName} - {VideoTitle}{ExplicitFlag}"
    SETTINGS.multiThread = False
    SETTINGS.apiKeyIndex = 4
    SETTINGS.checkExist = False

    Printf.settings()

    TIDAL_API.getPlaylistSelf()
    # test example
    # https://tidal.com/browse/track/70973230
    # track 70973230  77798028 212657
    start('242700165')
    # album 58138532  77803199  21993753   79151897  56288918
    # start('58138532')
    # playlist 98235845-13e8-43b4-94e2-d9f8e603cee7
    # start('98235845-13e8-43b4-94e2-d9f8e603cee7')
    # video 155608351 188932980 https://tidal.com/browse/track/55130637
    # start("155608351")https://tidal.com/browse/track/199683732


if __name__ == '__main__':
    # test()
    main()
