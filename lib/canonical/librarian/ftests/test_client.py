# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

import unittest
from cStringIO import StringIO

from canonical.testing import LaunchpadFunctionalLayer
from canonical.librarian.client import LibrarianClient
from canonical.librarian.interfaces import UploadFailed


class InstrumentedLibrarianClient(LibrarianClient):
    sentDatabaseName = False
    def _sendHeader(self, name, value):
        if name == 'Database-Name':
            self.sentDatabaseName = True
        return LibrarianClient._sendHeader(self, name, value)


class LibrarianClientTestCase(unittest.TestCase):
    layer = LaunchpadFunctionalLayer

    def test_addFileSendsDatabaseName(self):
        # addFile should send the Database-Name header.
        client = InstrumentedLibrarianClient()
        id1 = client.addFile('sample.txt', 6, StringIO('sample'), 'text/plain')
        self.failUnless(client.sentDatabaseName,
            "Database-Name header not sent by addFile")

    def test_remoteAddFileDoesntSendDatabaseName(self):
        # remoteAddFile should send the Database-Name header as well.
        client = InstrumentedLibrarianClient()
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

