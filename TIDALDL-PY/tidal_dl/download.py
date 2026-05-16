#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   download.py
@Time    :   2020/11/08
@Author  :   Yaronzz
@Version :   1.0
@Contact :   yaronhuang@foxmail.com
@Desc    :
'''

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import aigpy
import requests

from .decryption import *
from .printf import *
from .tidal import *


DOWNLOAD_TIMEOUT = (5, 60)
DEFAULT_PART_SIZE = 1048576
TRACK_THREAD_COUNT = 5
VIDEO_THREAD_COUNT = 8


def __removeFile__(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logging.warning("Unable to remove temporary file %s: %s", path, e)


def __ensureParentDir__(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def __remoteSize__(urls):
    if isinstance(urls, str):
        urls = [urls]

    total = 0
    for url in urls or []:
        size = aigpy.net.getSize(url)
        if size <= 0:
            return -1
        total += size
    return total


def __isSkip__(finalpath, urls):
    if not SETTINGS.checkExist:
        return False
    curSize = aigpy.file.getSize(finalpath)
    if curSize <= 0:
        return False
    netSize = __remoteSize__(urls)
    if netSize <= 0:
        return False
    return curSize >= netSize


def __encrypted__(stream, srcPath, descPath):
    if aigpy.string.isNull(stream.encryptionKey):
        os.replace(srcPath, descPath)
    else:
        key, nonce = decrypt_security_token(stream.encryptionKey)
        decrypt_file(srcPath, descPath, key, nonce)
        os.remove(srcPath)


def __parseContributors__(roleType, Contributors):
    if Contributors is None:
        return None
    try:
        ret = []
        for item in Contributors['items']:
            if item['role'] == roleType:
                ret.append(item['name'])
        return ret
    except:
        return None


def __setMetaData__(track: Track, album: Album, filepath, contributors, lyrics):
    obj = aigpy.tag.TagTool(filepath)
    obj.album = track.album.title
    obj.title = track.title
    if not aigpy.string.isNull(track.version):
        obj.title += ' (' + track.version + ')'

    obj.artist = list(map(lambda artist: artist.name, track.artists))
    obj.copyright = track.copyRight
    obj.tracknumber = track.trackNumber
    obj.discnumber = track.volumeNumber
    obj.composer = __parseContributors__('Composer', contributors)
    obj.isrc = track.isrc

    obj.albumartist = list(map(lambda artist: artist.name, album.artists))
    obj.date = album.releaseDate
    obj.totaldisc = album.numberOfVolumes
    obj.lyrics = lyrics
    if obj.totaldisc <= 1:
        obj.totaltrack = album.numberOfTracks
    coverpath = TIDAL_API.getCoverUrl(album.cover, "1280", "1280")
    obj.save(coverpath)


def downloadCover(album):
    if album is None:
        return False, "Album is empty."
    path = getAlbumPath(album) + '/cover.jpg'
    url = TIDAL_API.getCoverUrl(album.cover, "1280", "1280")
    if aigpy.string.isNull(url):
        return False, "Cover URL is empty."

    check, err = aigpy.net.downloadFile(url, path)
    if not check:
        msg = str(err)
        Printf.err(f"DL Cover[{album.title}] failed: {msg}")
        return False, msg
    return True, ''


def downloadAlbumInfo(album, tracks):
    if album is None:
        return

    path = getAlbumPath(album)
    aigpy.path.mkdirs(path)

    path += '/AlbumInfo.txt'
    infos = ""
    infos += "[ID]          %s\n" % (str(album.id))
    infos += "[Title]       %s\n" % (str(album.title))
    infos += "[Artists]     %s\n" % (TIDAL_API.getArtistsName(album.artists))
    infos += "[ReleaseDate] %s\n" % (str(album.releaseDate))
    infos += "[SongNum]     %s\n" % (str(album.numberOfTracks))
    infos += "[Duration]    %s\n" % (str(album.duration))
    infos += '\n'

    for index in range(0, album.numberOfVolumes):
        volumeNumber = index + 1
        infos += f"===========CD {volumeNumber}=============\n"
        for item in tracks:
            if item.volumeNumber != volumeNumber:
                continue
            infos += '{:<8}'.format("[%d]" % item.trackNumber)
            infos += "%s\n" % item.title
    aigpy.file.write(path, infos, "w+")


def downloadVideo(video: Video, album: Album = None, playlist: Playlist = None):
    title = getattr(video, 'title', None) or str(getattr(video, 'id', 'unknown'))
    try:
        stream = TIDAL_API.getVideoStreamUrl(video.id, SETTINGS.videoQuality)
        path = getVideoPath(video, album, playlist)
        partPath = path + '.part'

        Printf.video(video, stream)
        logging.info("[DL Video] name=" + aigpy.path.getFileName(path) + "\nurl=" + stream.m3u8Url)

        __ensureParentDir__(path)
        __removeFile__(partPath)

        response = requests.get(stream.m3u8Url, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        m3u8content = response.content
        if not m3u8content:
            Printf.err(f"DL Video[{title}] getM3u8 failed.")
            return False, "GetM3u8 failed."

        urls = aigpy.m3u8.parseTsUrls(m3u8content)
        if len(urls) <= 0:
            Printf.err(f"DL Video[{title}] getTsUrls failed.")
            return False, "GetTsUrls failed."

        check, msg = aigpy.m3u8.downloadByTsUrls(urls, partPath, VIDEO_THREAD_COUNT)
        if check:
            os.replace(partPath, path)
            Printf.success(title)
            return True, ''
        else:
            __removeFile__(partPath)
            Printf.err(f"DL Video[{title}] failed.{msg}")
            return False, msg
    except Exception as e:
        __removeFile__(locals().get('partPath', ''))
        Printf.err(f"DL Video[{title}] failed.{str(e)}")
        return False, str(e)


def downloadTrack(track: Track, album=None, playlist=None, userProgress=None, partSize=DEFAULT_PART_SIZE):
    title = getattr(track, 'title', None) or str(getattr(track, 'id', 'unknown'))
    try:
        stream = TIDAL_API.getStreamUrl(track.id, SETTINGS.audioQuality)
        path = getTrackPath(track, stream, album, playlist)
        partPath = path + '.part'

        if SETTINGS.showTrackInfo and not SETTINGS.multiThread:
            Printf.track(track, stream)

        if userProgress is not None:
            userProgress.updateStream(stream)

        # check exist
        if __isSkip__(path, stream.urls):
            Printf.success(aigpy.path.getFileName(path) + " (skip:already exists!)")
            return True, ''

        # download
        logging.info("[DL Track] name=" + aigpy.path.getFileName(path) + "\nurl=" + stream.url)

        __ensureParentDir__(path)
        __removeFile__(partPath)

        tool = aigpy.download.DownloadTool(partPath, stream.urls)
        tool.setUserProgress(userProgress)
        tool.setPartSize(partSize)
        check, err = tool.start(SETTINGS.showProgress and not SETTINGS.multiThread)
        if not check:
            __removeFile__(partPath)
            Printf.err(f"DL Track '{title}' failed: {str(err)}")
            return False, str(err)

        # encrypted -> decrypt and remove encrypted file
        __encrypted__(stream, partPath, path)

        # contributors
        try:
            contributors = TIDAL_API.getTrackContributors(track.id)
        except:
            contributors = None

        # lyrics
        try:
            lyrics = TIDAL_API.getLyrics(track.id).subtitles
            if SETTINGS.lyricFile:
                lrcPath = path.rsplit(".", 1)[0] + '.lrc'
                aigpy.file.write(lrcPath, lyrics, 'w')
        except:
            lyrics = ''

        __setMetaData__(track, album, path, contributors, lyrics)
        Printf.success(title)

        return True, ''
    except Exception as e:
        __removeFile__(locals().get('partPath', ''))
        Printf.err(f"DL Track '{title}' failed: {str(e)}")
        return False, str(e)


def downloadTracks(tracks, album: Album = None, playlist: Playlist = None):
    def __getAlbum__(item: Track):
        album = TIDAL_API.getAlbum(item.album.id)
        if SETTINGS.saveCovers and not SETTINGS.usePlaylistFolder:
            downloadCover(album)
        return album

    if not SETTINGS.multiThread:
        success = True
        for index, item in enumerate(tracks):
            itemAlbum = album
            if itemAlbum is None:
                itemAlbum = __getAlbum__(item)
                item.trackNumberOnPlaylist = index + 1
            check, _ = downloadTrack(item, itemAlbum, playlist)
            success = success and check
        return success
    else:
        futures = []
        with ThreadPoolExecutor(max_workers=TRACK_THREAD_COUNT) as thread_pool:
            for index, item in enumerate(tracks):
                itemAlbum = album
                if itemAlbum is None:
                    itemAlbum = __getAlbum__(item)
                    item.trackNumberOnPlaylist = index + 1
                futures.append(thread_pool.submit(downloadTrack, item, itemAlbum, playlist))

            success = True
            for future in as_completed(futures):
                check, msg = future.result()
                if not check:
                    success = False
                    logging.error("Track download failed: %s", msg)
            return success


def downloadVideos(videos, album: Album, playlist=None):
    success = True
    for item in videos:
        check, _ = downloadVideo(item, album, playlist)
        success = success and check
    return success
