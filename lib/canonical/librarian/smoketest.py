#! /usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Perform simple librarian operations to verify the current configuration.
"""

from cStringIO import StringIO
import datetime
import urllib

from zope.component import getUtility
import pytz
import transaction

from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet


FILE_SIZE = 1024
FILE_DATA = 'x' * FILE_SIZE
FILE_LIFETIME = datetime.timedelta(hours=1)


def store_file(client):
    file_id = client.addFile(
        'smoke-test-file', FILE_SIZE, StringIO(FILE_DATA), 'text/plain',
        expires=datetime.datetime.now(pytz.UTC)+FILE_LIFETIME)
    # To be able to retrieve the file, we must commit the current transaction.
    transaction.commit()
    alias = getUtility(ILibraryFileAliasSet)[file_id]
    return alias.http_url


def read_file(url):
    try:
        data = urllib.urlopen(url).read()
    except (MemoryError, KeyboardInterrupt, SystemExit):
        # Re-raise catastrophic errors.
        raise
    except:
        # An error is represented by returning None, which won't match when
        # comapred against FILE_DATA.
        return None

    return data


def do_smoketest(restricted_client, regular_client):
    print 'adding a private file to the librarian...'
    private_url = store_file(restricted_client)
    print 'retrieving private file from', private_url
    if read_file(private_url) != FILE_DATA:
        print 'ERROR: data fetched does not match data written'
        return 1

    print 'adding a public file to the librarian...'
    public_url = store_file(regular_client)
    print 'retrieving public file from', public_url
    if read_file(public_url) != FILE_DATA:
        print 'ERROR: data fetched does not match data written'
        return 1

    return 0
