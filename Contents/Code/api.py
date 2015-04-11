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

from urllib import urlencode
from common import MAILRU_URL

THUMB_RE = Regex('background-image\s*:\s*url\(\'([^\']+)\'\)')
GROUP_RE = Regex('/[a-z]+/([^/]+)')


def Request(method, params):
    HTTP.Headers['Cookie'] = Dict['auth']
    params['func_name'] = method
    params['ajax_call'] = 1
    params['ret_json'] = 1
    params.update(Dict['params'])

    res = JSON.ObjectFromURL(
        'http://my.mail.ru/cgi-bin/my/ajax?%s' % urlencode(params),
    )

    if res and len(res) > 2 and res[1] == 'OK':
        return res[len(res)-1]

    return False


def GetVideoItems(uid, album_id=None, offset=0, limit=0, ltype=None):
    if ltype is None:
        ltype = 'user' if '@' in uid else 'community_items'

    params = {
        'user': uid,
        'arg_type': ltype,
        'arg_limit': limit,
        'arg_offset': offset
    }

    if uid == 'pladform_video':
        params['arg_is_legal'] = 1

    if album_id is not None:
        if ltype == 'lvalbums':
            params['arg_category'] = album_id
        elif ltype == 'community_items':
            params['arg_album_id'] = album_id
        else:
            params['arg_album'] = album_id

    return Request('video.get_list', params)


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


def GetExternalMeta(meta):
    res = XML.ElementFromURL(
        'http://out.pladform.ru/getVideo?videoid=%s&pl=%s' % (
            meta['providerKey'],
            meta['meta']['playerId']
        )
    )

    if not res:
        return False

    ret = {
        'is_embed': False,
        'videos': {}
    }

    qmap = {
        'sd': '720',
        'ld': '360',
    }

    for src in res.findall('src'):
        etype = src.get('type')

        if etype == 'rutube':
            ret['is_embed'] = True
            ret['embed_url'] = 'http://rutube.ru/video/%s/' % src.text
            break
        elif etype == 'video':
            ret['videos'][qmap[src.get('quality')]] = src.text

    if not ret['videos'] and not ret['is_embed']:
        src = res.find('external_embed')
        if src:
            ret['is_embed'] = True
            ret['embed_url'] = src.text
            return ret
    else:
        return ret

    return False


def GroupFromElement(element):
    return GROUP_RE.search(element.get('href')).group(1)


def ImageFromElement(element):
    return THUMB_RE.search(element.get('style')).group(1)
