# -*- coding: utf-8 -*-

# Copyright (c) 2014, KOL
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import api as API
import proxy as Proxy
import common as Common

from updater import Updater
from zlib import crc32

PREFIX_V = '/video/mailru'
PREFIX_M = '/music/mailru'
PREFIX_P = '/photos/mailru'

ART = 'art-default.jpg'
ICON = 'icon-default.png'
ICON_V = 'icon-video.png'
ICON_M = 'icon-music.png'
ICON_P = 'icon-photo.png'
TITLE = u'%s' % L('Title')

###############################################################################
# Init
###############################################################################

def Start():
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = Common.MAILRU_USER_AGENT

    if ValidateAuth():
        Thread.Create(VideoProxy)


def ValidatePrefs():
    Dict.Reset()

    proxy_port = int(Prefs['proxy_port'])
    if (proxy_port < 1025 or proxy_port > 65534):
        return MessageContainer(
            header=u'%s' % L('Error'),
            message=u'%s' % L('IncorrectPort')
        )

    if (ValidateAuth()):
        return MessageContainer(
            header=u'%s' % L('Success'),
            message=u'%s' % L('Authorization complete')
        )
    else:
        return BadAuthMessage()


def ValidateAuth():
    return (Prefs['username'] and Prefs['password'] and API.CheckAuth())


###############################################################################
# Video
###############################################################################

@handler(PREFIX_V, u'%s' % L('VideoTitle'), thumb=ICON_V)
def VideoMainMenu():
    if not Dict['auth']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    Updater(PREFIX_V+'/update', oc)

    oc.add(DirectoryObject(
        key=Callback(VideoListChannels, uid=Prefs['username']),
        title=u'%s' % L('My channels')
    ))

    oc.add(DirectoryObject(
        key=Callback(VideoListGroups, uid=Prefs['username']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(VideoListFriends, uid=Prefs['username']),
        title=u'%s' % L('My friends')
    ))

    oc.add(DirectoryObject(
        key=Callback(VideoListChannels),
        title=u'%s' % L('All channels')
    ))

    oc.add(DirectoryObject(
        key=Callback(VideoCatalogueGroups),
        title=u'%s' % L('Catalogue')
    ))

    oc.add(InputDirectoryObject(
        key=Callback(
            VideoSearch,
            title=u'%s' % L('Search Video')
        ),
        title=u'%s' % L('Search'), prompt=u'%s' % L('Search Video')
    ))

    return AddVideoAlbums(oc, Prefs['username'])


@route(PREFIX_V + '/groups')
def VideoListGroups(uid, offset=0):
    return Common.GetGroups(VideoAlbums, VideoListGroups, uid, offset);


@route(PREFIX_V + '/friends')
def VideoListFriends(uid, offset=0):
    return Common.GetFriends(VideoAlbums, VideoListFriends, uid, offset)


@route(PREFIX_V + '/albums')
def VideoAlbums(uid, title, offset=0, path='/my/'):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )
    return AddVideoAlbums(oc, uid, offset)


@route(PREFIX_V + '/channels')
def VideoListChannels(uid=None, offset=0):
    return Common.GetChannels(VideoAlbums, VideoListChannels, uid, offset)


@route(PREFIX_V + '/catalogue/groups')
def VideoCatalogueGroups():
    oc = ObjectContainer(
        title2=u'%s' % L('Catalogue'),
    )

    for cat, title in {
        'movies': L('Фильмы'),
        'serials': L('Сериалы'),
        'show': L('Телешоу'),
        'mults': L('Мультфильмы'),
        'music': L('Музыка'),
        'tnt': L('ТНТ'),
    }.items():
        oc.add(DirectoryObject(
            key=Callback(
                VideoCatalogueAlbums, cat=cat,
                title=u'%s' % title,
            ),
            title=u'%s' % title,
        ))

    return oc


@route(PREFIX_V + '/catalogue/albums')
def VideoCatalogueAlbums(cat, title, offset=0):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )

    albums = API.GetVideoItems(
        uid=Prefs['username'],
        ltype='lvalbums',
        arg_category=cat,
        offset=offset,
        limit=Prefs['video_per_page']
    )

    if albums and albums['total']:
        for item in albums['items']:

            if 'VideoUrl' in item:
                oc.add(GetVideoObject(item))
            else:
                title = u'%s' % item['Name']

                oc.add(DirectoryObject(
                    key=Callback(
                        VideoList,
                        uid='pladform_video',
                        title=title,
                        album_id=item['Album']
                    ),
                    title=title,
                    summary=u'%s' % item['Description'],
                    thumb=item['PreviewUrl']
                ))

        offset = int(offset)+int(Prefs['video_per_page'])
        if albums['total'] == int(Prefs['video_per_page']):
            oc.add(NextPageObject(
                key=Callback(
                    VideoCatalogueAlbums,
                    cat=cat,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    return oc


@route(PREFIX_V + '/list')
def VideoList(uid, title, album_id=None, offset=0, ltype=None, **kwargs):

    res = API.GetVideoItems(
        uid=uid,
        ltype=ltype,
        album_id=album_id,
        offset=offset,
        limit=Prefs['video_per_page'],
        **kwargs
    )

    if not res or not res['total']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=u'%s' % title,
        content=ContainerContent.GenericVideos,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        try:
            oc.add(GetVideoObject(item))
        except Exception as e:
            try:
                Log.Warn('Can\'t add video to list: %s', e.status)
            except:
                continue

    offset = int(offset)+int(Prefs['video_per_page'])
    if offset < res['total']:
        oc.add(NextPageObject(
            key=Callback(
                VideoList,
                uid=uid,
                title=title,
                ltype=ltype,
                album_id=album_id,
                offset=offset,
                **kwargs
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


@route(PREFIX_V + '/view')
def VideoView(url):

    try:
        res = JSON.ObjectFromURL(url)
    except:
        res = None
        pass

    if not res or 'meta' not in res:
        raise Ex.MediaNotAvailable

    meta = {  # Emulate list item
        'MetaUrl': url,
        'Title': res['meta']['title'],
        'UrlHtml': res['meta']['url'].replace(Common.MAILRU_URL, ''),
        'Comment':  '',
        'ImageUrlI': res['meta']['poster'],
        'Time': res['meta']['timestamp'],
        'Duration': res['meta']['duration'],
        'HDexist': False,
    }

    ext_meta = False

    if not 'videos' in res:
        ext_meta = API.GetExternalMeta(res)
    else:
        meta['HDexist'] = len(res['videos']) > 1

    return ObjectContainer(
        objects=[GetVideoObject(meta, ext_meta)],
        content=ContainerContent.GenericVideos
    )


def VideoSearch(query, title=u'%s' % L('Search'), offset=0):
    return VideoList(
        Prefs['username'],
        title,
        offset=offset,
        ltype='search',
        arg_tag=query,
        arg_hd_exists=1 if Prefs['search_hd'] else '',
        arg_unsafe=1 if Prefs['search_adult'] else '',
    )


@route(PREFIX_V + '/proxy')
def VideoProxy():
    Proxy.Server()


def AddVideoAlbums(oc, uid, offset=0):
    albums = API.Request('video.get_albums', {
        'user': uid,
        'arg_limit': Common.MAILRU_LIMIT,
        'arg_offset': offset
    })

    # First album is default
    has_albums = albums and albums['total'] > 1
    offset = int(offset)

    if not offset:
        if not has_albums and not len(oc.objects):
            return VideoList(uid=uid, title=u'%s' % L('All videos'))
        else:
            oc.add(DirectoryObject(
                key=Callback(
                    VideoList, uid=uid,
                    title=u'%s' % L('All videos'),
                ),
                title=u'%s' % L('All videos'),
            ))


    if has_albums:
        for item in albums['items']:
            # display playlist title and number of videos
            title = u'%s: %s (%d)' % (L('Album'), item['Name'], item['Count'])

            oc.add(DirectoryObject(
                key=Callback(
                    VideoList, uid=uid,
                    title=u'%s' % item['Name'],
                    ltype='album_items',
                    album_id=item['ID']
                ),
                title=title,
                thumb=item['CoverImgPath']
            ))

        offset = offset+Common.MAILRU_LIMIT
        if offset < albums['total']:
            oc.add(NextPageObject(
                key=Callback(
                    VideoAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    return oc


def GetVideoObject(item, ext_meta=False):

    if ext_meta and ext_meta['external']:
        return URLService.MetadataObjectForURL(ext_meta['external'])

    API.CheckMetaUrl(item)

    resolutions = {}
    if ext_meta:
        for r in ext_meta['videos']:
            resolutions[r] = Proxy.GetUrl(
                item['MetaUrl'],
                r,
                ext_meta['videos'][r]['url']
            )
    else:
        resolutions['360'] = Proxy.GetUrl(item['MetaUrl'], '360')
        if item['HDexist']:
            resolutions['480'] = Proxy.GetUrl(item['MetaUrl'], '480')
            resolutions['720'] = Proxy.GetUrl(item['MetaUrl'], '720')


    return VideoClipObject(
        key=Callback(
            VideoView,
            url=item['MetaUrl'],
        ),
        rating_key='%s' % item['UrlHtml'],
        title=u'%s' % item['Title'],
        source_title=TITLE,
        summary=item['Comment'],
        thumb=item['ImageUrlI'],
        source_icon=R(ICON),
        originally_available_at=Datetime.FromTimestamp(item['Time']),
        duration=(item['Duration']*1000),
        items=[
            MediaObject(
                parts=[PartObject(
                    key=resolutions[r]
                )],
                video_resolution=r,
                container=Container.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                optimized_for_streaming=True
            ) for r in sorted(resolutions.keys(), reverse=True)
        ]
    )


###############################################################################
# Music
###############################################################################

@handler(PREFIX_M, u'%s' % L('MusicTitle'), thumb=ICON_M)
def MusicMainMenu():
    if not Dict['auth']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    Updater(PREFIX_M+'/update', oc)

    oc.add(DirectoryObject(
        key=Callback(MusicListGroups, uid=Prefs['username']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(MusicListFriends, uid=Prefs['username']),
        title=u'%s' % L('My friends')
    ))
    oc.add(DirectoryObject(
        key=Callback(MusicList, uid=Prefs['username'], title=L('My music')),
        title=u'%s' % L('My music')
    ))
    oc.add(DirectoryObject(
        key=Callback(
            MusicRecomendations,
            uid=Prefs['username'],
            title=L('Recomendations')
        ),
        title=u'%s' % L('Recomendations')
    ))
    oc.add(DirectoryObject(
        key=Callback(MusicCollections),
        title=u'%s' % L('Collections')
    ))
    oc.add(InputDirectoryObject(
        key=Callback(
            MusicSearch,
            title=u'%s' % L('Search Music')
        ),
        title=u'%s' % L('Search'), prompt=u'%s' % L('Search Music')
    ))

    return oc


@route(PREFIX_M + '/groups')
def MusicListGroups(uid, offset=0):
    return Common.GetGroups(MusicList, MusicListGroups, uid, offset)


@route(PREFIX_M + '/friends')
def MusicListFriends(uid, offset=0):
    return Common.GetFriends(MusicList, MusicListFriends, uid, offset)


@route(PREFIX_M + '/list')
def MusicList(uid, title, offset=0, path='/my/'):
    return Common.GetMusicList(
        init_object=GetTrackObject,
        callback_page=MusicList,
        title=title,
        uid=uid,
        offset=offset,
        res=API.Request('audio.get', {
            'user': uid,
            'arg_limit': Prefs['audio_per_page'],
            'arg_offset': offset
        })
    )


@route(PREFIX_M + '/recomendations')
def MusicRecomendations(uid, title, offset=0):
    return Common.GetMusicList(
        init_object=GetTrackObject,
        callback_page=MusicRecomendations,
        title=title,
        uid=uid,
        offset=0,
        res=API.GetMusicRecomendations()
    )


@route(PREFIX_M + '/collections')
def MusicCollections(offset=0):
    res = API.Request('music.collections', {
        'arg_limit': Common.MAILRU_LIMIT,
        'arg_offset': offset,
    })

    if not res or not res['Total']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=u'%s' % L('Collections'),
        replace_parent=(offset > 0)
    )

    for item in res['Data']:
        title = u'%s' % item['Name']
        summary = ', '.join(item['tags'])
        if item['Description']:
            summary = u"%s\n%s" % (summary, item['Description'])

        oc.add(DirectoryObject(
            key=Callback(
                MusicCollection, uid='',
                title=title,
            ),
            title=title,
            thumb=item['CoverCroped'],
            summary=u'%s' % summary
        ))

    offset = int(offset)+Common.MAILRU_LIMIT
    if offset < res['Total']:
        oc.add(NextPageObject(
            key=Callback(MusicCollections, offset=offset),
            title=u'%s' % L('Next page')
        ))
    return oc


@route(PREFIX_M + '/collections/view')
def MusicCollection(uid, title, offset=0):
    return Common.GetMusicList(
        init_object=GetTrackObject,
        callback_page=MusicCollection,
        title=title,
        uid=uid,
        offset=0,
        res=API.Request('music.collection', {
            'arg_limit': Prefs['audio_per_page'],
            'arg_offset': offset,
            'arg_name': title,
        })
    )


@route(PREFIX_M + '/play')
def MusicPlay(info):

    item = JSON.ObjectFromString(info)

    if not item:
        raise Ex.MediaNotAvailable

    return ObjectContainer(
        objects=[GetTrackObject(item)],
        content=ContainerContent.Tracks
    )


def MusicSearch(query, title=u'%s' % L('Search'), offset=0):
    return Common.GetMusicList(
        init_object=GetTrackObject,
        callback_page=MusicList,
        title=title,
        uid=Prefs['username'],
        offset=offset,
        res=API.Request('music.search', {
            'arg_limit': Prefs['audio_per_page'],
            'arg_offset': offset,
            'arg_query': query,
        })
    )


def GetTrackObject(item):
    url = item['URL']
    if url[:2] == '//':
        url = 'http:'+url

    track_id = item['TrackID'] if 'TrackID' in item else '0'
    if not track_id and 'FileID' in item:
        track_id = crc32(item['FileID'])

    info = JSON.StringFromObject({
        'TrackID': track_id,
        'Name': item['Name'],
        'Author': item['Author'],
        'DurationInSeconds': item['DurationInSeconds'],
        'URL': url,
    })
    return TrackObject(
        key=Callback(MusicPlay, info=info),
        rating_key=track_id,
        title=u'%s' % item['Name'],
        artist=u'%s' % item['Author'],
        duration=int(item['DurationInSeconds'])*1000,
        items=[
            MediaObject(
                parts=[PartObject(key=Proxy.GetUrl(d_url=url))],
                container=Container.MP3,
                audio_codec=AudioCodec.MP3,
                audio_channels=2,
                video_codec='',  # Crutch for disable generate parts,
                optimized_for_streaming=True,
            )
        ]
    )


###############################################################################
# Photos
###############################################################################

@handler(PREFIX_P, u'%s' % L('PhotosTitle'), thumb=ICON_P)
def PhotoMainMenu():
    if not Dict['auth']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    Updater(PREFIX_P+'/update', oc)

    oc.add(DirectoryObject(
        key=Callback(PhotoListGroups, uid=Dict['username']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(PhotoListFriends, uid=Dict['username']),
        title=u'%s' % L('My friends')
    ))

    return AddPhotoAlbums(oc, Dict['username'])


@route(PREFIX_P + '/groups')
def PhotoListGroups(uid, offset=0):
    return Common.GetGroups(PhotoAlbums, PhotoListGroups, uid, offset)


@route(PREFIX_P + '/friends')
def PhotoListFriends(uid, offset=0):
    return Common.GetFriends(PhotoAlbums, PhotoListFriends, uid, offset)


@route(PREFIX_P + '/albums')
def PhotoAlbums(uid, title, offset=0, path='/my/'):
    oc = ObjectContainer(title2=u'%s' % title, replace_parent=(offset > 0))
    AddPhotoAlbums(oc, uid, path)
    if not len(oc) == 1:
        return PhotoList(uid, title, '')

    return oc


@route(PREFIX_P + '/list')
def PhotoList(uid, title, album_id, offset=0):
    photos = API.Request('photo.photostream', {
        'user': uid,
        'arg_album_id': album_id,
        'arg_limit': Prefs['photos_per_page'],
        'arg_offset': offset

    }, True)

    if not photos or len(photos) < 5 or not photos[4]:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content='photo',
        replace_parent=(offset > 0)
    )

    total = int(photos[4])
    items = HTML.ElementFromString(photos[3]).xpath(
        '//div[contains(@class, "b-catalog__photo-item")]'
    )

    for item in items:
        try:
            link = item.find('a[@class="b-catalog__photo-item-img"]')
            oc.add(PhotoObject(
                key=link.get('data-filedimageurl'),
                rating_key='%s%s' % (Common.MAILRU_URL, link.get('href')),
                thumb=API.ImageFromElement(item)
            ))
        except:
            pass

    offset = int(offset)+int(Prefs['photos_per_page'])
    if offset < total:
        oc.add(NextPageObject(
            key=Callback(
                PhotoList,
                uid=uid,
                title=title,
                album_id=album_id,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


def AddPhotoAlbums(oc, uid, path='/my/'):
    albums = API.GetPhotoAlbums(uid, path)

    if not albums:
        return

    if len(albums):
        for item in albums:
            link = item.xpath(
                './a[contains(@class, "b-catalog__photo-albums-item-img")]'
            )[0]
            title = u'%s' % item.xpath(
                './/a[contains(@class, "b-catalog__photo-albums-item-name")]'
            )[0].text
            oc.add(DirectoryObject(
                key=Callback(
                    PhotoList, uid=uid,
                    title=title,
                    album_id=API.AlbumFromElement(link)
                ),
                title=title,
                thumb=API.ImageFromElement(link),
            ))

    if not len(oc.objects):
        return Common.NoContents()

    return oc


###############################################################################
# Common
###############################################################################

def BadAuthMessage():
    return MessageContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('NotAuth')
    )
