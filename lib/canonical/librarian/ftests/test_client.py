# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

import unittest
import textwrap
from cStringIO import StringIO

import transaction

from canonical.testing import DatabaseLayer, LaunchpadFunctionalLayer
from canonical.config import config
from canonical.database.sqlbase import block_implicit_flushes
from canonical.librarian.client import (
    LibrarianClient, RestrictedLibrarianClient)
from canonical.librarian.interfaces import UploadFailed
from canonical.launchpad.database import LibraryFileAlias


class InstrumentedLibrarianClient(LibrarianClient):
    sentDatabaseName = False
    def _sendHeader(self, name, value):
        if name == 'Database-Name':
            self.sentDatabaseName = True
        return LibrarianClient._sendHeader(self, name, value)

    called_getURLForDownload = False
    def _getURLForDownload(self, aliasID):
        self.called_getURLForDownload = True
        return LibrarianClient._getURLForDownload(self, aliasID)


class LibrarianClientTestCase(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def test_addFileSendsDatabaseName(self):
        # addFile should send the Database-Name header.
        client = InstrumentedLibrarianClient()
        id1 = client.addFile(
            'sample.txt', 6, StringIO('sample'), 'text/plain')
        self.failUnless(client.sentDatabaseName,
            "Database-Name header not sent by addFile")

    def test_remoteAddFileDoesntSendDatabaseName(self):
        # remoteAddFile should send the Database-Name header as well.
        client = InstrumentedLibrarianClient()
        # Because the remoteAddFile call commits to the database in a
        # different process, we need to explicitly tell the DatabaseLayer to
        # fully tear down and set up the database.
        DatabaseLayer.force_dirty_database()
        id1 = client.remoteAddFile('sample.txt', 6, StringIO('sample'),
                                   'text/plain')
        self.failUnless(client.sentDatabaseName,
            "Database-Name header not sent by remoteAddFile")

    def test_clientWrongDatabase(self):
        # If the client is using the wrong database, the server should refuse
        # the upload, causing LibrarianClient to raise UploadFailed.
        client = LibrarianClient()
        # Force the client to mis-report its database
        client._getDatabaseName = lambda cur: 'wrong_database'
        try:
            client.addFile('sample.txt', 6, StringIO('sample'), 'text/plain')
        except UploadFailed, e:
            msg = e.args[0]
            self.failUnless(
                msg.startswith('Server said: 400 Wrong database'),
                'Unexpected UploadFailed error: ' + msg)
        else:
            self.fail("UploadFailed not raised")

    def test__getURLForDownload(self):
        # This protected method is used by getFileByAlias. It is supposed to
        # use the internal host and port rather than the external, proxied
        # host and port. This is to provide relief for our own issues with the
        # problems reported in bug 317482.
        #
        # (Set up:)
        client = LibrarianClient()
        alias_id = client.addFile(
            'sample.txt', 6, StringIO('sample'), 'text/plain')
        config.push(
            'test config',
            textwrap.dedent('''\
                [librarian]
                download_host: example.org
                download_port: 1234
                '''))
        try:
            # (Test:)
            # The LibrarianClient should use the download_host and
            # download_port.
            expected_host = 'http://example.org:1234/'
            download_url = client._getURLForDownload(alias_id)
            self.failUnless(download_url.startswith(expected_host),
                            'expected %s to start with %s' % (download_url,
                                                              expected_host))
            # If the alias has been deleted, _getURLForDownload returns None.
            lfa = LibraryFileAlias.get(alias_id)
            lfa.content.deleted = True
            call = block_implicit_flushes( # Prevent a ProgrammingError
                LibrarianClient._getURLForDownload)
            self.assertEqual(call(client, alias_id), None)
        finally:
            # (Tear down:)
            config.pop('test config')

    def test_restricted_getURLForDownload(self):
        # The RestrictedLibrarianClient should use the
        # restricted_download_host and restricted_download_port, but is
        # otherwise identical to the behavior of the LibrarianClient discussed
        # and demonstrated above.
        #
        # (Set up:)
        client = RestrictedLibrarianClient()
        alias_id = client.addFile(
            'sample.txt', 6, StringIO('sample'), 'text/plain')
        config.push(
            'test config',
            textwrap.dedent('''\
                [librarian]
                restricted_download_host: example.com
                restricted_download_port: 5678
                '''))
        try:
            # (Test:)
            # The LibrarianClient should use the download_host and
            # download_port.
            expected_host = 'http://example.com:5678/'
            download_url = client._getURLForDownload(alias_id)
            self.failUnless(download_url.startswith(expected_host),
                            'expected %s to start with %s' % (download_url,
                                                              expected_host))
            # If the alias has been deleted, _getURLForDownload returns None.
            lfa = LibraryFileAlias.get(alias_id)
            lfa.content.deleted = True
            call = block_implicit_flushes( # Prevent a ProgrammingError
                RestrictedLibrarianClient._getURLForDownload)
            self.assertEqual(call(client, alias_id), None)
        finally:
            # (Tear down:)
            config.pop('test config')

    def test_getFileByAlias(self):
        # This method should use _getURLForDownload to download the file.
        # We use the InstrumentedLibrarianClient to show that it is consulted.
        #
        # (Set up:)
        client = InstrumentedLibrarianClient()
        alias_id = client.addFile(
            'sample.txt', 6, StringIO('sample'), 'text/plain')
        transaction.commit() # Make sure the file is in the "remote" database
        self.failIf(client.called_getURLForDownload)
        # (Test:)
        f = client.getFileByAlias(alias_id)
        self.assertEqual(f.read(), 'sample')
        self.failUnless(client.called_getURLForDownload)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
