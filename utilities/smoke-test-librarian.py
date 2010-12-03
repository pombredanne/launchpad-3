#! /usr/bin/python -S
#
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Create a static WADL file describing the current webservice.

Example:

    % LPCONFIG=development bin/py utilities/create-lp-wadl-and-apidoc.py \\
      "lib/canonical/launchpad/apidoc/wadl-development-%(version)s.xml"
"""
import _pythonpath # Not lint, actually needed.

from cStringIO import StringIO
import datetime
import optparse
import os
import sys
import urllib

from zope.component import getUtility
import pytz
import transaction

from canonical.config import config
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.librarian.interfaces import (
    IRestrictedLibrarianClient,
    ILibrarianClient,
    )


FILE_SIZE = 1024
FILE_DATA = 'x' * FILE_SIZE
FILE_LIFETIME = datetime.timedelta(hours=1)


def store_file(client):
    file_id = client.addFile(
        'smoke-test-file', FILE_SIZE, StringIO(FILE_DATA), 'text/plain',
        expires=datetime.datetime.now(pytz.UTC)+FILE_LIFETIME)
    alias = getUtility(ILibraryFileAliasSet)[file_id]
    transaction.commit()
    return alias.http_url


def main():
    print 'adding a private file to the librarian...'
    restricted_client = getUtility(IRestrictedLibrarianClient)
    private_url = store_file(restricted_client)
    print 'retrieving private file from', private_url
    if urllib.urlopen(private_url).read() != FILE_DATA:
        print 'ERROR: data fetched does not match data written'
        return 1

    print 'adding a public file to the librarian...'
    regular_client = getUtility(ILibrarianClient)
    public_url = store_file(regular_client)
    print 'retrieving public file from', public_url
    if urllib.urlopen(public_url).read() != FILE_DATA:
        print 'ERROR: data fetched does not match data written'
        return 1

    return 0


if __name__ == '__main__':
    execute_zcml_for_scripts()
    sys.exit(main())
