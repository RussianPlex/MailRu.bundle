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

MAILRU_URL = 'http://my.mail.ru/'
MAILRU_LIMIT = 50
MAILRU_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux i686; rv:32.0) '
    'Gecko/20100101 Firefox/32.0'
)


def GetGroups(callback_action, callback_page, uid, offset):
    '''Get groups container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My groups'),
        replace_parent=(offset > 0)
    )
    groups = API.Request('groups.get_groups', {
        'user': uid,
        'arg_offset': offset
    })

    if groups and groups['total']:
        items = HTML.ElementFromString(groups['html'])

        for item in items.xpath('//div[@data-group="item"]'):
            info = item.xpath('.//a[contains(@class, "groups__name")]')[0]

            title = u'%s' % info.text_content()

            try:
                thumb = API.ImageFromElement(item.xpath(
                    './/a[contains(@class, "groups__avatar")]'
                )[0])
            except:
                thumb = None
                pass

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=API.GroupFromElement(info),
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


def GetChannels(callback_action, callback_page, uid, offset):
    '''Get groups container with custom callback'''
    if uid:
        method = 'video_channel.get_channels'
        title = u'%s' % L('My channels')
    else:
        method = 'video_channel.get_channels_catalogue'
        title = u'%s' % L('All channels')

    items = API.Request(method, {
        'user': uid,
        'arg_offset': offset,
        'arg_limit': MAILRU_LIMIT,
    })

    if items:
        items = HTML.ElementFromString(items)

    if not items:
        return NoContents()

    oc = ObjectContainer(
        title2=title,
        replace_parent=(offset > 0)
    )

    for item in items.xpath('//div[@data-type="item"]'):
        info = item.xpath(
            './/a[contains(@class, "b-catalog__channel-item__name")]'
        )[0]

        title = u'%s' % info.text_content()

        try:
            thumb = API.ImageFromElement(item.xpath(
                './/a[contains(@class, "b-catalog__channel-item__avatar")]'
            )[0])
        except:
            thumb = None
            pass

        oc.add(DirectoryObject(
            key=Callback(
                callback_action,
                uid=API.GroupFromElement(info),
                title=title,
            ),
            title=title,
            thumb=thumb
        ))

    return oc


def GetFriends(callback_action, callback_page, uid, offset):
    '''Get friends container with custom callback'''
    oc = ObjectContainer(
        title2=u'%s' % L('My friends'),
        replace_parent=(offset > 0)
    )

    friends = API.Request('video.friends', {
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

            oc.add(DirectoryObject(
                key=Callback(
                    callback_action,
                    uid=item['Email'],
                    title=title,
                ),
                title=title,
                thumb=item['Avatar180URL']
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


def NoContents():
    return ObjectContainer(
        header=u'%s' % L('Error'),
        message=u'%s' % L('No entries found')
    )
