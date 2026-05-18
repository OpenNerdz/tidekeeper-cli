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
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import aigpy
import requests

from .decryption import *
from .printf import *
from .tidal import *


DOWNLOAD_TIMEOUT = (5, 60)
DEFAULT_PART_SIZE = 1048576
TRACK_THREAD_COUNT = 5
VIDEO_THREAD_COUNT = 8
DOWNLOAD_RETRIES = 4
DOWNLOAD_CHUNK_SIZE = 256 * 1024
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
FAILED_TRACKS_FILE = "failed-tracks.txt"
failed_track_log_lock = Lock()


def __removeFile__(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as e:
        logging.warning("Unable to remove temporary file %s: %s", path, e)


def __removeDir__(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
    except OSError as e:
        logging.warning("Unable to remove temporary directory %s: %s", path, e)


def __failedTrackLogPath__():
    return os.path.join(SETTINGS.downloadPath or ".", FAILED_TRACKS_FILE)


def __tidalTrackUrl__(track):
    return f"https://tidal.com/browse/track/{getattr(track, 'id', '')}"


def __oneLine__(value):
    return " ".join(str(value).split())


def __logFailedTrack__(track, album=None, playlist=None, reason=""):
    track_id = getattr(track, 'id', None)
    if track_id is None:
        return

    try:
        path = __failedTrackLogPath__()
        __ensureParentDir__(path)
        context = []
        album_title = getattr(album, 'title', None)
        playlist_title = getattr(playlist, 'title', None)
        if album_title:
            context.append(f"album={__oneLine__(album_title)}")
        if playlist_title:
            context.append(f"playlist={__oneLine__(playlist_title)}")

        title = getattr(track, 'title', None) or str(track_id)
        parts = [
            time.strftime("%Y-%m-%d %H:%M:%S"),
            f"track={__oneLine__(title)}",
            f"id={track_id}",
        ]
        parts.extend(context)
        if reason:
            parts.append(f"reason={__oneLine__(reason)}")
        entry = "# " + " | ".join(parts) + "\n" + __tidalTrackUrl__(track) + "\n"

        with failed_track_log_lock:
            with open(path, "a", encoding="utf-8") as output:
                output.write(entry)
    except Exception as e:
        logging.warning("Unable to log failed track %s: %s", track_id, e)


def __ensureParentDir__(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def __retryDelay__(response, attempt):
    if response is not None and response.headers.get("Retry-After"):
        try:
            return min(float(response.headers["Retry-After"]), 60)
        except ValueError:
            pass
    return min(2 ** attempt, 20)


def __httpRequest__(method, url, **kwargs):
    last_error = None
    for attempt in range(DOWNLOAD_RETRIES):
        response = None
        try:
            response = requests.request(method, url, timeout=DOWNLOAD_TIMEOUT, **kwargs)
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < DOWNLOAD_RETRIES - 1:
                response.close()
                time.sleep(__retryDelay__(response, attempt))
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            last_error = e
            if response is not None:
                response.close()
            if attempt < DOWNLOAD_RETRIES - 1:
                time.sleep(__retryDelay__(response, attempt))
                continue
            raise
    raise last_error


def __contentLength__(url):
    try:
        response = __httpRequest__("HEAD", url, allow_redirects=True)
        response.close()
        length = response.headers.get("Content-Length")
        return int(length) if length is not None else -1
    except Exception:
        return -1


def __remoteSize__(urls):
    if isinstance(urls, str):
        urls = [urls]

    total = 0
    for url in urls or []:
        size = __contentLength__(url)
        if size <= 0:
            return -1
        total += size
    return total


def __setUserProgressMax__(userProgress, size):
    if userProgress is None or size <= 0:
        return
    try:
        userProgress.setMaxNum(size)
    except Exception:
        pass


def __addUserProgress__(userProgress, size):
    if userProgress is None or size <= 0:
        return
    try:
        userProgress.addCurNum(size)
    except Exception:
        pass


def __downloadUrlToPath__(url, path, progress=None, userProgress=None, progressLock=None, chunkSize=DOWNLOAD_CHUNK_SIZE):
    tempPath = path + '.part'
    __removeFile__(tempPath)
    response = __httpRequest__("GET", url, stream=True, allow_redirects=True)
    try:
        with open(tempPath, "wb") as output:
            for chunk in response.iter_content(chunk_size=chunkSize):
                if not chunk:
                    continue
                output.write(chunk)
                size = len(chunk)
                if progress is not None:
                    progress.addCurCount(size)
                if progressLock is not None:
                    with progressLock:
                        __addUserProgress__(userProgress, size)
                else:
                    __addUserProgress__(userProgress, size)
        os.replace(tempPath, path)
    finally:
        response.close()
        __removeFile__(tempPath)


def __downloadUrls__(
        urls,
        outputPath,
        showProgress=False,
        userProgress=None,
        threadNum=1,
        chunkSize=DOWNLOAD_CHUNK_SIZE,
        probeSize=True):
    urls = [url for url in (urls or []) if not aigpy.string.isNull(url)]
    if len(urls) <= 0:
        return False, "URL list is empty."

    __ensureParentDir__(outputPath)
    __removeFile__(outputPath)

    totalSize = __remoteSize__(urls) if probeSize else -1
    progress = None
    if totalSize > 0:
        __setUserProgressMax__(userProgress, totalSize)
        if showProgress:
            progress = aigpy.progress.ProgressTool(totalSize, 15, unit="B")

    if len(urls) == 1 or threadNum <= 1:
        try:
            with open(outputPath, "wb") as output:
                for url in urls:
                    response = __httpRequest__("GET", url, stream=True, allow_redirects=True)
                    try:
                        for chunk in response.iter_content(chunk_size=chunkSize):
                            if not chunk:
                                continue
                            output.write(chunk)
                            size = len(chunk)
                            if progress is not None:
                                progress.addCurCount(size)
                            __addUserProgress__(userProgress, size)
                    finally:
                        response.close()
            return True, ''
        except Exception as e:
            __removeFile__(outputPath)
            return False, str(e)

    partsDir = outputPath + '.parts'
    __removeDir__(partsDir)
    os.makedirs(partsDir, exist_ok=True)
    progressLock = Lock()

    try:
        with ThreadPoolExecutor(max_workers=threadNum) as thread_pool:
            futures = []
            for index, url in enumerate(urls):
                partPath = os.path.join(partsDir, f"{index:08d}.part")
                futures.append(thread_pool.submit(
                    __downloadUrlToPath__,
                    url,
                    partPath,
                    progress,
                    userProgress,
                    progressLock,
                    chunkSize,
                ))

            for future in as_completed(futures):
                future.result()

        with open(outputPath, "wb") as output:
            for index in range(len(urls)):
                partPath = os.path.join(partsDir, f"{index:08d}.part")
                with open(partPath, "rb") as inputFile:
                    shutil.copyfileobj(inputFile, output)
        return True, ''
    except Exception as e:
        __removeFile__(outputPath)
        return False, str(e)
    finally:
        __removeDir__(partsDir)


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


def __lyricsText__(value):
    if value is None:
        return ''
    text = str(value)
    return text if text.strip() else ''


def __lyricsPayload__(lyricsData):
    if lyricsData is None:
        return '', '', ''

    subtitles = __lyricsText__(getattr(lyricsData, 'subtitles', None))
    lyrics = __lyricsText__(getattr(lyricsData, 'lyrics', None))
    metadataLyrics = lyrics or subtitles

    if subtitles:
        return metadataLyrics, subtitles, '.lrc'
    if lyrics:
        return metadataLyrics, lyrics, '.txt'
    return '', '', ''


def __writeLyricsFile__(trackPath, lyricsData):
    metadataLyrics, fileLyrics, extension = __lyricsPayload__(lyricsData)
    if SETTINGS.lyricFile and fileLyrics:
        lyricPath = trackPath.rsplit(".", 1)[0] + extension
        aigpy.file.write(lyricPath, fileLyrics, 'w')
    return metadataLyrics


def __saveLyricsForTrack__(trackId, trackPath):
    try:
        return __writeLyricsFile__(trackPath, TIDAL_API.getLyrics(trackId))
    except Exception as e:
        logging.info("Unable to save lyrics for track %s: %s", trackId, e)
        return ''


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

    check, err = __downloadUrls__([url], path, SETTINGS.showProgress, threadNum=1)
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

        response = __httpRequest__("GET", stream.m3u8Url, allow_redirects=True)
        try:
            m3u8content = response.content
            if not m3u8content:
                Printf.err(f"DL Video[{title}] getM3u8 failed.")
                return False, "GetM3u8 failed."
        finally:
            response.close()

        urls = aigpy.m3u8.parseTsUrls(m3u8content)
        if len(urls) <= 0:
            Printf.err(f"DL Video[{title}] getTsUrls failed.")
            return False, "GetTsUrls failed."

        check, msg = __downloadUrls__(
            urls,
            partPath,
            SETTINGS.showProgress,
            threadNum=VIDEO_THREAD_COUNT,
            probeSize=False,
        )
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
            if SETTINGS.lyricFile:
                __saveLyricsForTrack__(track.id, path)
            Printf.success(aigpy.path.getFileName(path) + " (skip:already exists!)")
            return True, ''

        # download
        logging.info("[DL Track] name=" + aigpy.path.getFileName(path) + "\nurl=" + stream.url)

        __ensureParentDir__(path)
        __removeFile__(partPath)

        check, err = __downloadUrls__(
            stream.urls,
            partPath,
            SETTINGS.showProgress and not SETTINGS.multiThread,
            userProgress,
            TRACK_THREAD_COUNT if SETTINGS.multiThread else 1,
            max(int(partSize), 64 * 1024),
        )
        if not check:
            __removeFile__(partPath)
            __logFailedTrack__(track, album, playlist, err)
            Printf.err(f"DL Track '{title}' failed: {str(err)}")
            return False, str(err)

        # encrypted -> decrypt and remove encrypted file
        __encrypted__(stream, partPath, path)

        # contributors
        try:
            contributors = TIDAL_API.getTrackContributors(track.id)
        except:
            contributors = None

        lyrics = __saveLyricsForTrack__(track.id, path)

        try:
            __setMetaData__(track, album, path, contributors, lyrics)
        except Exception as e:
            logging.warning("Unable to write metadata for %s: %s", path, e)
            Printf.info(f"Downloaded '{title}', but metadata tagging was skipped: {str(e)}")
        Printf.success(title)

        return True, ''
    except Exception as e:
        __removeFile__(locals().get('partPath', ''))
        __logFailedTrack__(track, album, playlist, e)
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
