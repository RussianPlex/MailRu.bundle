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
    # HTTP.CacheTime = CACHE_1HOUR
    HTTP.CacheTime = 0 # FIXME
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
            Search,
            search_type='video',
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
def VideoAlbums(uid, title, offset=0):
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
        title2=L('Catalogue'),
    )

    for cat, title in {
        'movies': L('Фильмы'),
        'serials': L('Сериалы'),
        'show': L('Телешоу'),
        'mults': L('Мультфильмы'),
        'music': L('Музыка'),
        'tnt': L('ТНТ'),
    }.iteritems():
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
        album_id=cat,
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
def VideoList(uid, title, album_id=None, offset=0, ltype=None):

    res = API.GetVideoItems(
        uid=uid,
        ltype=ltype,
        album_id=album_id,
        offset=offset,
        limit=Prefs['video_per_page']
    )

    if not res or not res['total']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content=ContainerContent.GenericVideos,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        GetVideoObject(item)
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
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


@route(PREFIX_V + '/view')
def VideoView(vid, url):

    try:
        res = JSON.ObjectFromURL(url)
    except:
        res = None
        pass

    if not res or 'meta' not in res:
        raise Ex.MediaNotAvailable

    meta = {  # Emulate list item
        'MetaUrl': url,
        'ItemId': vid,
        'Title': res['meta']['title'],
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

    Log.Debug(ext_meta)

    return ObjectContainer(
        objects=[GetVideoObject(meta, ext_meta)],
        content=ContainerContent.GenericVideos
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

    if ext_meta and ext_meta['is_embed']:
        return URLService.MetadataObjectForURL(ext_meta['embed_url'])

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
            vid=item['ItemId'],
            url=item['MetaUrl'],
        ),
        rating_key='%s' % item['ItemId'],
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
    oc.add(DirectoryObject(
        key=Callback(MusicListGroups, uid=Prefs['username']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(MusicListFriends, uid=Prefs['username']),
        title=u'%s' % L('My friends')
    ))

    oc.add(InputDirectoryObject(
        key=Callback(
            Search,
            search_type='audio',
            title=u'%s' % L('Search Music')
        ),
        title=u'%s' % L('Search'), prompt=u'%s' % L('Search Music')
    ))

    return AddMusicAlbums(oc, Prefs['username'])


@route(PREFIX_M + '/groups')
def MusicListGroups(uid, offset=0):
    return Common.GetGroups(MusicAlbums, MusicListGroups, uid, offset)


@route(PREFIX_M + '/friends')
def MusicListFriends(uid, offset=0):
    return Common.GetFriends(MusicAlbums, MusicListFriends, uid, offset)


@route(PREFIX_M + '/albums')
def MusicAlbums(uid, title, offset=0):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )
    return AddMusicAlbums(oc, uid, offset)


@route(PREFIX_M + '/list')
def MusicList(uid, title, album_id=None, offset=0):

    params = {
        'owner_id': uid,
        'count': Prefs['audio_per_page'],
        'offset': offset
    }
    if album_id is not None:
        params['album_id'] = album_id

    res = API.Request('audio.get', params)

    if not res or not res['count']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content=ContainerContent.Tracks,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetTrackObject(item))

    offset = int(offset)+Common.MAILRU_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                MusicList,
                uid=uid,
                title=title,
                album_id=album_id,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


@route(PREFIX_M + '/play')
def MusicPlay(info):

    item = JSON.ObjectFromString(info)

    if not item:
        raise Ex.MediaNotAvailable

    return ObjectContainer(
        objects=[GetTrackObject(item)],
        content=ContainerContent.Tracks
    )


# TODO - does not support
def AddMusicAlbums(oc, uid, offset=0):

    albums = API.Request('audio.getAlbums', {
        'owner_id': uid,
        'count': Common.MAILRU_LIMIT,
        'offset': offset
    })

    has_albums = albums and albums['count']
    offset = int(offset)

    if not offset:
        if not has_albums and not len(oc.objects):
            return MusicList(uid=uid, title=u'%s' % L('All music'))
        else:
            oc.add(DirectoryObject(
                key=Callback(
                    MusicList, uid=uid,
                    title=u'%s' % L('All music'),
                ),
                title=u'%s' % L('All music'),
            ))

    if has_albums:
        for item in albums['items']:
            # display playlist title and number of videos
            title = u'%s: %s' % (L('Album'), item['title'])

            oc.add(DirectoryObject(
                key=Callback(
                    MusicList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                title=title,
            ))

        offset = offset+Common.MAILRU_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    MusicAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    return oc


def GetTrackObject(item):
    return TrackObject(
        key=Callback(MusicPlay, info=JSON.StringFromObject(item)),
        # rating_key='%s.%s' % (Plugin.Identifier, item['id']),
        # Rating key must be integer because PHT and PlexConnect
        # does not support playing queue with string rating key
        rating_key=item['id'],
        title=u'%s' % item['title'],
        artist=u'%s' % item['artist'],
        duration=int(item['duration'])*1000,
        items=[
            MediaObject(
                parts=[PartObject(key=item['url'])],
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
    oc.add(DirectoryObject(
        key=Callback(PhotoListGroups, uid=Dict['user_id']),
        title=u'%s' % L('My groups')
    ))
    oc.add(DirectoryObject(
        key=Callback(PhotoListFriends, uid=Dict['user_id']),
        title=u'%s' % L('My friends')
    ))

    return AddPhotoAlbums(oc, Dict['user_id'])


@route(PREFIX_P + '/groups')
def PhotoListGroups(uid, offset=0):
    return Common.GetGroups(PhotoAlbums, PhotoListGroups, uid, offset)


@route(PREFIX_P + '/friends')
def PhotoListFriends(uid, offset=0):
    return Common.GetFriends(PhotoAlbums, PhotoListFriends, uid, offset)


@route(PREFIX_P + '/albums')
def PhotoAlbums(uid, title, offset=0):
    oc = ObjectContainer(title2=u'%s' % title, replace_parent=(offset > 0))
    return AddPhotoAlbums(oc, uid, offset)


@route(PREFIX_P + '/list')
def PhotoList(uid, title, album_id, offset=0):
    res = API.Request('photos.get', {
        'owner_id': uid,
        'album_id': album_id,
        'extended': 0,
        'photo_sizes': 1,
        'rev': 1,
        'count': Prefs['photos_per_page'],
        'offset': offset
    })

    if not res or not res['count']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content='photo',
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetPhotoObject(item))

    offset = int(offset)+Common.MAILRU_LIMIT
    if offset < res['count']:
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


def AddPhotoAlbums(oc, uid, offset=0):

    albums = API.Request('photos.getAlbums', {
        'owner_id': uid,
        'need_covers': 1,
        'photo_sizes': 1,
        'need_system': 1,
        'count': Common.MAILRU_LIMIT,
        'offset': offset
    })

    has_albums = albums and albums['count']
    offset = int(offset)

    if has_albums:
        for item in albums['items']:
            thumb = ''
            for size in item['sizes']:
                if size['type'] == 'p':
                    thumb = size['src']
                    break

            oc.add(DirectoryObject(
                key=Callback(
                    PhotoList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                summary=item['description'] if 'description' in item else '',
                title=u'%s (%s)' % (item['title'], item['size']),
                thumb=thumb,
            ))

        offset = offset+Common.MAILRU_LIMIT
        if offset < albums['count']:
            oc.add(NextPageObject(
                key=Callback(
                    PhotoAlbums,
                    uid=uid,
                    title=oc.title2,
                    offset=offset
                ),
                title=u'%s' % L('More albums')
            ))

    if not len(oc.objects):
        return Common.NoContents()

    return oc


def GetPhotoObject(item):

    sizes = {}
    for size in item['sizes']:
        sizes[size['type']] = size['src']

    url = ''
    for size in ['z', 'y', 'x']:
        if size in sizes:
            url = sizes[size]
            break

    return PhotoObject(
        key=url,
        rating_key='%s.%s' % (Plugin.Identifier, item['id']),
        summary=u'%s' % item['text'],
        thumb=sizes['p'] if 'p' in sizes else ''
    )


###############################################################################
# Common
###############################################################################

def Search(query, title=u'%s' % L('Search'), search_type='video', offset=0):

    is_video = search_type == 'video'

    params = {
        'sort': 2,
        'offset': offset,
        'count': Prefs[search_type + '_per_page'],
        'q': query
    }

    if is_video:
        if Prefs['search_hd']:
            params['hd'] = 1
        if Prefs['search_adult']:
            params['adult'] = 1

    res = API.Request(search_type+'.search', params)

    if not res or not res['count']:
        return Common.NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        replace_parent=(offset > 0),
    )

    if is_video:
        method = GetVideoObject
        oc.content = ContainerContent.GenericVideos
    else:
        method = GetTrackObject
        oc.content = ContainerContent.Tracks

    for item in res['items']:
        oc.add(method(item))

    offset = int(offset)+Common.MAILRU_LIMIT
    if offset < res['count']:
        oc.add(NextPageObject(
            key=Callback(
                Search,
                query=query,
                title=title,
                search_type=search_type,
                offset=offset
            ),
            title=u'%s' % L('Next page')
        ))

    return oc


def BadAuthMessage():
    return MessageContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('NotAuth')
    )
