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

from urllib import urlencode
from SimpleHTTPServer import SimpleHTTPRequestHandler
from common import MAILRU_USER_AGENT


def GetUrl(url, key):
    return 'http://%s:%d/?%s' % (
        Network.Address,
        int(Prefs['proxy_port']),
        urlencode({
            'url': url,
            'key': key
        })
    )


def Server():
    httpd = SocketServer.ForkingTCPServer(
        (Network.Address, int(Prefs['proxy_port'])),
        Handler
    )
    Log.Debug('Start proxy on  %s:%d' % (
        Network.Address,
        int(Prefs['proxy_port'])
    ))
    httpd.serve_forever()


class Handler(SimpleHTTPRequestHandler):
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
