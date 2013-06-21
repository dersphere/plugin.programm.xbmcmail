#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from xbmcswift2 import Plugin, xbmc, xbmcgui
from resources.lib.client import XBMCMailClient, InvalidCredentials

STRINGS = {
    # Root menu entries
}


plugin = Plugin()


@plugin.route('/')
def show_root():
    items = [{
        'label': mailbox['name'],
        'path': plugin.url_for(
            endpoint='show_mailbox',
            mailbox=mailbox['name'],
        )
    } for mailbox in client.get_mailboxes()]
    return plugin.finish(items)


@plugin.route('/<mailbox>/')
def show_mailbox(mailbox):

    def _format_label(email):
        label = '[B]%s[/B] - %s' % (
            _format_from(email['from']),
            _format_subject(email['subject']),
        )
        if email['unread']:
            label = '[COLOR red]%s[/COLOR]' % label
        return label

    def _format_from(s):
        if ' <' in s:
            return s.split(' <')[0].strip('"')
        else:
            return s.split('@')[0]

    def _format_subject(s):
        return s.replace('\r\n', '')

    items = [{
        'label': _format_label(email),
        'path': plugin.url_for(
            endpoint='show_mailbox',
            mailbox=email['id'],
        )
    } for email in client.get_emails(mailbox)]
    return plugin.finish(items)


def login():
    logged_in = False
    while not logged_in:
        try:
            client = XBMCMailClient(
                username=plugin.get_setting('username', unicode),
                password=plugin.get_setting('password', unicode),
                host=plugin.get_setting('host', unicode),
                use_ssl=plugin.get_setting('use_ssl', bool),
            )
        except InvalidCredentials:
            try_again = xbmcgui.Dialog().yesno(
                _('connection_error'),
                _('wrong_credentials'),
                _('want_set_now')
            )
            if not try_again:
                return
            plugin.open_settings()
        else:
            logged_in = True
    return client


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id])
    else:
        log('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    client = login()
    if client:
        plugin.run()
        client.logout()
