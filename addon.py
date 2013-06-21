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

    def _format_label(mailbox):
        label = mailbox['name']
        if 'unseen' in mailbox and 'total' in mailbox:
            label = u'%s (%d/%d)' % (
                label,
                int(mailbox['unseen']),
                int(mailbox['total']),
            )
        return label

    items = [{
        'label': _format_label(mailbox),
        'path': plugin.url_for(
            endpoint='show_mailbox',
            mailbox=mailbox['name'],
        )
    } for mailbox in client.get_mailboxes()]
    return plugin.finish(items)


@plugin.route('/<mailbox>/')
def show_mailbox(mailbox):

    def context_menu(mailbox, email):
        items = []
        if email['unseen']:
            items.append(
                (_('email_mark_seen'),
                 _view(endpoint='email_mark_seen',
                       mailbox=mailbox,
                       email_id=email['id']))
            )
        else:
            items.append(
                (_('email_mark_unseen'),
                 _view(endpoint='email_mark_unseen',
                       mailbox=mailbox,
                       email_id=email['id']))
            )
        items.append(
            (_('email_delete'),
             _view(endpoint='email_delete',
                   mailbox=mailbox,
                   email_id=email['id']))
        )
        return items

    def _format_label(email):
        label = '[B]%s[/B] - %s' % (
            _format_from(email['from']),
            _format_subject(email['subject']),
        )
        if email['unseen']:
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
        'replace_context_menu': True,
        'context_menu': context_menu(mailbox, email),
        'path': plugin.url_for(
            endpoint='email_show',
            mailbox=email['mailbox'],
            email_id=email['id']
        )
    } for email in client.get_emails(mailbox)]
    return plugin.finish(items)


@plugin.route('/<mailbox>/<email_id>/mark_seen')
def email_mark_seen(mailbox, email_id):
    client.email_mark_seen(email_id, mailbox)
    _refresh_view()


@plugin.route('/<mailbox>/<email_id>/mark_unseen')
def email_mark_unseen(mailbox, email_id):
    client.email_mark_unseen(email_id, mailbox)
    _refresh_view()


@plugin.route('/<mailbox>/<email_id>/delete')
def email_delete(mailbox, email_id):
    confirmed = xbmcgui.Dialog().yesno(
        _('delete'),
        _('are_you_sure')
    )
    if not confirmed:
        return
    client.email_delete(email_id, mailbox)
    _refresh_view()


@plugin.route('/<mailbox>/<email_id>/show')
def email_show(mailbox, email_id):
    xbmc.executebuiltin('ActivateWindow(%d)' % 10147)
    window = xbmcgui.Window(10147)
    email = client.get_email(email_id, mailbox)
    header = '%s - %s' % (email['from'], email['subject'])
    text = '\r\n'.join((
        '=====================================================',
        '[B]From:[/B] %s' % email['from'],
        '[B]To:[/B] %s' % email['to'],
        '[B]Date:[/B] %s' % email['date'],
        '[B]Subject:[/B] %s' % email['subject'],
        '=====================================================',
        email['body_text'],
    ))
    window.getControl(1).setLabel(header)
    window.getControl(5).setText(text)


def _run(*args, **kwargs):
    return 'XBMC.RunPlugin(%s)' % plugin.url_for(*args, **kwargs)


def _view(*args, **kwargs):
    return 'XBMC.Container.Update(%s)' % plugin.url_for(*args, **kwargs)


def _refresh_view():
    xbmc.executebuiltin('Container.Refresh')


def _login():
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
        plugin.log.debug('String is missing: %s' % string_id)
        return string_id


if __name__ == '__main__':
    client = _login()
    if client:
        plugin.run()
        client.logout()
