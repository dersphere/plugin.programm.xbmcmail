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

from email.parser import HeaderParser
from email.Header import decode_header
import imaplib
import re


class InvalidCredentials(Exception):
    pass


class XBMCMailClient(object):

    re_list_response = re.compile(r'\((.*?)\) "(.*)" (.*)')

    def __init__(self, *args, **kwargs):
        self._reset_connection()
        if args or kwargs:
            self.connect(*args, **kwargs)

    def __parse_list_response(self, line):
        flags, delimiter, name = self.re_list_response.match(line).groups()
        name = name.strip('"')
        return (flags, delimiter, name)

    def __parse_header(self, line):
        if line:
            return decode_header(line)[0][0]
        return 'FIXME'

    def _reset_connection(self):
        self.connected = False
        self.connection = None
        self.selected = None

    def connect(self, username=None, password=None, host=None, use_ssl=True):
        self.log('connecting to server %s' % host)
        try:
            cls = imaplib.IMAP4_SSL if use_ssl else imaplib.IMAP4
            self.connection = cls(host)
            self.connection.login(username, password)
        except cls.error, error:
            self.log(error)
            self._reset_connection()
            if 'credentials' in error.message.lower():
                raise InvalidCredentials(error)
            else:
                raise error
        self.connected = True
        self.log('connected.')
        return self.connected

    def _list_folders(self, *args, **kwargs):
        # FIXME: parse status
        self.log('list')
        ret, data = self.connection.list(*args, **kwargs)
        self.log(ret)
        return (self.__parse_list_response(line) for line in data)

    def _select_folder(self, folder_id, *args, **kwargs):
        self.log('select %s' % folder_id)
        ret, data = self.connection.select(folder_id)
        self.log(ret)
        self.selected = folder_id
        return int(data[0])

    def _get_email_ids(self, folder_id=None, criteria='UNDELETED'):
        if folder_id and folder_id != self.selected:
            self._select_folder(folder_id)
        if not self.selected:
            raise Exception
        self.log('search %s' % criteria)
        ret, data = self.connection.search(None, criteria)
        self.log(ret)
        message_ids = data[0].split()
        message_ids.reverse()
        return message_ids

    def _fetch_emails_by_ids(self, message_ids, folder_id=None, parts='(BODY.PEEK[HEADER])'):
        if folder_id and folder_id != self.selected:
            self._select_folder(folder_id)
        if not self.selected:
            raise Exception
        if isinstance(message_ids, (list, tuple)):
            message_ids = ','.join(message_ids)
        MESSAGE_PARTS = '(BODY.PEEK[HEADER])'
        self.log('fetch %s' % message_ids)
        ret, data = self.connection.fetch(message_ids, parts)
        self.log(ret)
        data = (d for d in data if isinstance(d, tuple))
        parser = HeaderParser()
        data = ((i.split()[0], parser.parsestr(h)) for i, h in data)
        return data

    def get_folders(self, *args, **kwargs):
        folders = [{
            'name': name,
            'folder_id': name,
            'has_children': 'HasChildren' in flags,
        } for flags, d, name in self._list_folders(*args, **kwargs)]
        return folders

    def get_emails(self, folder_id, limit=100, offset=0):
        num_mails = self._select_folder(folder_id)

        message_ids = self._get_email_ids()
        message_ids = message_ids[offset:limit + offset]

        messages = [{
            'id': msg_id,
            'subject': self.__parse_header(msg.get('Subject')),
            'from': self.__parse_header(msg.get('From')),
        } for msg_id, msg in self._fetch_emails_by_ids(message_ids)]
        messages.reverse()
        return messages

    def get_email(self, email_id):
        pass

    def log(self, text):
        print u'[%s]: %s' % (self.__class__.__name__, repr(text))

    def logout(self):
        if self.connected:
            self.log('closing connection...')
            if self.selected:
                self.connection.close()
            self.connection.logout()
            self.log('closed.')

    def __del__(self):
        self.logout()
