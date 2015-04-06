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

import urllib2
import SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from urllib import urlencode

PREFIX_V = '/video/mailru'
PREFIX_M = '/music/mailru'
PREFIX_P = '/photos/mailru'

ART = 'art-default.jpg'
ICON = 'icon-default.png'
ICON_V = 'icon-video.png'
ICON_M = 'icon-music.png'
ICON_P = 'icon-photo.png'
TITLE = u'%s' % L('Title')

MAILRU_URL = 'http://my.mail.ru/'
MAILRU_LIMIT = 50
MAILRU_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux i686; rv:32.0) '
    'Gecko/20100101 Firefox/32.0'
)


###############################################################################
# Init
###############################################################################

def Start():

    # HTTP.CacheTime = CACHE_1HOUR
    HTTP.CacheTime = 0 # FIXME
    HTTP.Headers['User-Agent'] = MAILRU_USER_AGENT

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
    return (Prefs['username'] and Prefs['password'] and CheckAuth())


###############################################################################
# Video
###############################################################################

@handler(PREFIX_V, u'%s' % L('VideoTitle'), thumb=ICON_V)
def VideoMainMenu():
    if not Dict['auth']:
        return BadAuthMessage()

    oc = ObjectContainer(title2=TITLE, no_cache=True)

    oc.add(DirectoryObject(
        key=Callback(VideoListGroups, uid=Prefs['username']),
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
        key=Callback(VideoListGroups, uid=Prefs['username']),
        title=u'%s' % L('Catalogues')
    ))

    oc.add(DirectoryObject(
        key=Callback(VideoListGroups, uid=Prefs['username']),
        title=u'%s' % L('Channels')
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
    return oc


@route(PREFIX_V + '/groups')
def VideoListGroups(uid, offset=0):
    return GetGroups(VideoAlbums, VideoListGroups, uid, offset);


@route(PREFIX_V + '/friends')
def VideoListFriends(uid, offset=0):
    return GetFriends(VideoAlbums, VideoListFriends, uid, offset)


@route(PREFIX_V + '/albums')
def VideoAlbums(uid, title, offset=0):
    oc = ObjectContainer(
        title2=u'%s' % title,
        replace_parent=(offset > 0)
    )
    return AddVideoAlbums(oc, uid, offset)


@route(PREFIX_V + '/list')
def VideoList(uid, title, album_id=None, offset=0):

    params = {
        'user': uid,
        'arg_limit': Prefs['video_per_page'],
        'arg_offset': offset
    }

    if '@' in uid:  # user
        params['arg_type'] = 'user'
    else:           # group
        params['arg_type'] = 'community_items'

    if album_id is not None:
        params['arg_album'] = album_id

    res = ApiRequest('video.get_list', params)

    if not res or not res['total']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
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

    offset = res['offset']
    if offset < res['total']:
        oc.add(NextPageObject(
            key=Callback(
                VideoList,
                uid=uid,
                title=title,
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
        return NoContents()

    return ObjectContainer(
        objects=[GetVideoObject({  # Emulate list item
            'MetaUrl': url,
            'ItemId': vid,
            'Title': res['meta']['title'],
            'Comment':  '',
            'ImageUrlI': res['meta']['poster'],
            'Time': res['meta']['timestamp'],
            'Duration': res['meta']['duration'],
            'HDexist': len(res['videos']) > 1,
        })],
        content=ContainerContent.GenericVideos
    )


@route(PREFIX_V + '/proxy')
def VideoProxy():
    httpd = SocketServer.ForkingTCPServer(
        (Network.Address, int(Prefs['proxy_port'])),
        VideoProxyHandler
    )
    Log.Debug('Start proxy on  %s:%d' % (
        Network.Address,
        int(Prefs['proxy_port'])
    ))
    httpd.serve_forever()


def AddVideoAlbums(oc, uid, offset=0):
    # albums = ApiRequest('video.getAlbums', {
    #     'owner_id': uid,
    #     'extended': 1,
    #     'count': MAILRU_LIMIT,
    #     'offset': offset
    # })

    # has_albums = albums and albums['count']

    has_albums = False
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
            title = u'%s: %s (%d)' % (L('Album'), item['title'], item['count'])
            if 'photo_320' in item:
                thumb = item['photo_320']
            else:
                thumb = R(ICON)

            oc.add(DirectoryObject(
                key=Callback(
                    VideoList, uid=uid,
                    title=u'%s' % item['title'],
                    album_id=item['id']
                ),
                title=title,
                thumb=thumb
            ))

        offset = offset+MAILRU_LIMIT
        if offset < albums['count']:
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


def GetVideoObject(item):

    resolutions = ['360']
    if item['HDexist']:
        resolutions.append('480')
        resolutions.append('720')
        resolutions.reverse()

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
                    key='http://%s:%d/?%s' % (
                        Network.Address,
                        int(Prefs['proxy_port']),
                        urlencode({
                            'url': item['MetaUrl'],
                            'key': r+'p'
                        })
                    )
                )],
                video_resolution=r,
                container=Container.MP4,
                video_codec=VideoCodec.H264,
                audio_codec=AudioCodec.AAC,
                optimized_for_streaming=True
            ) for r in resolutions
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
    return GetGroups(MusicAlbums, MusicListGroups, uid, offset)


@route(PREFIX_M + '/friends')
def MusicListFriends(uid, offset=0):
    return GetFriends(MusicAlbums, MusicListFriends, uid, offset)


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

    res = ApiRequest('audio.get', params)

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content=ContainerContent.Tracks,
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetTrackObject(item))

    offset = int(offset)+MAILRU_LIMIT
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


def AddMusicAlbums(oc, uid, offset=0):

    albums = ApiRequest('audio.getAlbums', {
        'owner_id': uid,
        'count': MAILRU_LIMIT,
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

        offset = offset+MAILRU_LIMIT
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
    return GetGroups(PhotoAlbums, PhotoListGroups, uid, offset)


@route(PREFIX_P + '/friends')
def PhotoListFriends(uid, offset=0):
    return GetFriends(PhotoAlbums, PhotoListFriends, uid, offset)


@route(PREFIX_P + '/albums')
def PhotoAlbums(uid, title, offset=0):
    oc = ObjectContainer(title2=u'%s' % title, replace_parent=(offset > 0))
    return AddPhotoAlbums(oc, uid, offset)


@route(PREFIX_P + '/list')
def PhotoList(uid, title, album_id, offset=0):
    res = ApiRequest('photos.get', {
        'owner_id': uid,
        'album_id': album_id,
        'extended': 0,
        'photo_sizes': 1,
        'rev': 1,
        'count': Prefs['photos_per_page'],
        'offset': offset
    })

    if not res or not res['count']:
        return NoContents()

    oc = ObjectContainer(
        title2=(u'%s' % title),
        content='photo',
        replace_parent=(offset > 0)
    )

    for item in res['items']:
        oc.add(GetPhotoObject(item))

    offset = int(offset)+MAILRU_LIMIT
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

    albums = ApiRequest('photos.getAlbums', {
        'owner_id': uid,
        'need_covers': 1,
        'photo_sizes': 1,
        'need_system': 1,
        'count': MAILRU_LIMIT,
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

        offset = offset+MAILRU_LIMIT
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
        return NoContents()

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

    res = ApiRequest(search_type+'.search', params)

    if not res or not res['count']:
        return NoContents()

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

    offset = int(offset)+MAILRU_LIMIT
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


def NoContents():
    return ObjectContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('No entries found')
    )


def NormalizeExternalUrl(url):
    # Rutube service crutch
    if Regex('//rutube.ru/[^/]+/embed/[0-9]+').search(url):
        url = HTML.ElementFromURL(url, cacheTime=CACHE_1WEEK).xpath(
            '//link[contains(@rel, "canonical")]'
        )
        if url:
            return url[0].get('href')

    return url


def GetGroups(callback_action, callback_page, uid, offset):
    '''Get groups container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My groups'),
        replace_parent=(offset > 0)
    )
    groups = ApiRequest('groups.get_groups', {
        'user': uid,
        'arg_offset': offset
    })

    if groups and groups['total']:
        items = HTML.ElementFromString(groups['html'])

        for item in items.xpath('//div[@data-group="item"]'):
            info = item.xpath('.//a[contains(@class, "groups__name")]')[0]

            title = u'%s' % info.text_content()

            try:
                thumb = ImageFromElementStyle(item.xpath(
                    './/a[contains(@class, "groups__avatar")]'
                )[0])
            except:
                thumb = R(ICON)
                pass

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=info.get('href'),
                    title=title,
                ),
                title=title,
                thumb=thumb
            ))

        if groups['next_page_size'] > 0:
            oc.add(NextPageObject(
                key=Callback(
                    callback_page,
                    uid=uid,
                    offset=groups['new_offset']
                ),
                title=u'%s' % L('More groups')
            ))

    return oc


def GetFriends(callback_action, callback_page, uid, offset):
    '''Get friends container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My friends'),
        replace_parent=(offset > 0)
    )

    # TODO &mna=643427&mnb=995542408
    friends = ApiRequest('video.friends', {
        'user': uid,
        'arg_limit': MAILRU_LIMIT,
        'arg_offset': offset
    })

    if friends and friends['Total'] and len(friends['Data']):
        '''
        Avatar32URL, FirstName, Avatar180URL, AvatarChangeTime,
        SmallAvatarURL, Dir, AuID, LastName, VideoCount,
        Email, Name, IsFemale
        '''
        for item in friends['Data']:
            title = u'%s' % item['Name']
            if 'Avatar180URL' in item:
                thumb = item['Avatar180URL']
            else:
                thumb = R(ICON)

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=item['Email'],
                    title=title,
                ),
                title=title,
                thumb=thumb
            ))

        offset = friends['NewOffset']
        if offset < friends['Total']:
            oc.add(NextPageObject(
                key=Callback(
                    callback_page,
                    uid=uid,
                    offset=offset
                ),
                title=u'%s' % L('Next page')
            ))

    return oc


def ImageFromElementStyle(element):
    return Regex(
        'background-image\s*:\s*url\(\'([^\']+)\'\)'
    ).search(
        element.get('style')
    ).group(1)


def ApiRequest(method, params):
    HTTP.Headers['Cookie'] = Dict['auth']
    params['func_name'] = method
    params['ajax_call'] = 1
    params['ret_json'] = 1
    params.update(Dict['params'])

# http://my.mail.ru/cgi-bin/my/ajax?user=vladimirsleptsov1961@bk.ru&ajax_call=1&func_name=video.get_list&mna=671969&mnb=2210013916&arg_type=related&arg_limit=40&arg_offset=0&arg_item_id=&arg_is_legal=0&arg_pwidth=120&arg_pheight=67
# http://my.mail.ru/cgi-bin/my/ajax?user=vladimirsleptsov1961@bk.ru&ajax_call=1&func_name=video.get_list&mna=671969&mnb=2210013916&arg_type=user&arg_limit=40&arg_item_id=13&arg_offset_item_id=0&arg_offset=0&arg_pwidth=120&arg_pheight=67

    res = JSON.ObjectFromURL(
        'http://my.mail.ru/cgi-bin/my/ajax?%s' % urlencode(params),
    )

    # Log.Debug(res)

    if res and len(res) > 2 and res[1] == 'OK':
        return res[len(res)-1]

    return False


def CheckAuth():
    HTTP.ClearCookies()
    Dict['auth'] = False

    res = HTTP.Request(
        'https://auth.mail.ru/cgi-bin/auth',
        {
            'page': MAILRU_URL,
            'FailPage': MAILRU_URL+'cgi-bin/login?fail=1',
            'Login': Prefs['username'],
            'Domain': 'mail.ru',
            'Password': Prefs['password']
        },
        cacheTime=0
    )

    if (res and Prefs['username'] in HTTP.CookiesForURL(MAILRU_URL)):
        res = HTTP.Request(
            (
                'https://auth.mail.ru/sdc?fail=http:%2F%2Fmy.mail.ru'
                '%2Fcgi-bin%2Flogin&from=http%3A%2F%2Fmy.mail.ru%2F'
            ),
            cacheTime=0
        )
        if 'set-cookie' in res.headers:
            try:
                res = JSON.ObjectFromString(
                    HTML.ElementFromString(res.content).xpath(
                        '//script[@data-mru-fragment="client-server"]'
                    )[0].text_content()
                )
                Log.Debug(res)
                del res['magic']['myhost']

                Dict['auth'] = HTTP.CookiesForURL(MAILRU_URL)
                Dict['params'] = res['magic']
                return True
            except:
                pass

    return False


class VideoProxyHandler(SimpleHTTPRequestHandler):
    def do_GET(self):

        Log.Debug('Proxy request %s' % self.path)

        params = dict([
            p.split('=') for p in self.path[
                self.path.index('?')+1:
            ].split('&')
        ])

        try:
            info = JSON.ObjectFromURL(
                urllib2.url2pathname(params['url']),
                cacheTime=0
            )
        except:
            info = None

        if not info or 'videos' not in info:
            self.send_error(403)
            return None

        info = info['videos']
        url = None
        for item in info:
            if item['key'] == params['key']:
                url = item['url']
                break

        if not url:
            url = info[len(info)-1]['url']

        Log.Debug('Start processing %s' % url)
        headers = self.headers

        Log.Debug(headers)

        del headers['Host']
        del headers['Referer']
        headers['Cookie'] = HTTP.CookiesForURL(url)
        headers['User-Agent'] = MAILRU_USER_AGENT

        self.copyfile(
            urllib2.urlopen(urllib2.Request(url, headers=headers)),
            self.wfile
        )
