# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from fixtures import MockPatchObject
from pymacaroons import Macaroon
from testtools.testcase import ExpectedException
from testtools.twistedsupport import AsynchronousDeferredRunTest
import transaction
from twisted.internet import (
    defer,
    reactor,
    )
from twisted.internet.threads import deferToThread
from twisted.web import (
    server,
    xmlrpc,
    )

from lp.services.database.interfaces import IStore
from lp.services.librarian.model import LibraryFileContent
from lp.services.librarianserver import db
from lp.testing import TestCase
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import LaunchpadZopelessLayer
from lp.xmlrpc import faults


class DBTestCase(TestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(DBTestCase, self).setUp()
        switch_dbuser('librarian')

    def test_lookupByDigest(self):
        # Create library
        library = db.Library()

        # Initially it should be empty
        self.assertEqual([], library.lookupBySHA1('deadbeef'))

        # Add a file, check it is found by lookupBySHA1
        fileID = library.add('deadbeef', 1234, 'abababab', 'babababa')
        self.assertEqual([fileID], library.lookupBySHA1('deadbeef'))

        # Add a new file with the same digest
        newFileID = library.add('deadbeef', 1234, 'abababab', 'babababa')
        # Check it gets a new ID anyway
        self.assertNotEqual(fileID, newFileID)
        # Check it is found by lookupBySHA1
        self.assertEqual(sorted([fileID, newFileID]),
                         sorted(library.lookupBySHA1('deadbeef')))

        aliasID = library.addAlias(fileID, 'file1', 'text/unknown')
        alias = library.getAlias(aliasID, None, '/')
        self.assertEqual('file1', alias.filename)
        self.assertEqual('text/unknown', alias.mimetype)


class FakeAuthServer(xmlrpc.XMLRPC):
    """A fake authserver.

    This saves us from needing to start an appserver in tests.
    """

    def __init__(self):
        xmlrpc.XMLRPC.__init__(self)
        self.macaroons = set()

    def registerMacaroon(self, macaroon, context):
        self.macaroons.add((macaroon.serialize(), context))

    def xmlrpc_verifyMacaroon(self, macaroon_raw, context):
        if (macaroon_raw, context) in self.macaroons:
            return True
        else:
            return faults.Unauthorized()


class TestLibrarianStuff(TestCase):
    """Tests for the librarian."""

    layer = LaunchpadZopelessLayer
    run_tests_with = AsynchronousDeferredRunTest.make_factory(timeout=10)

    def setUp(self):
        super(TestLibrarianStuff, self).setUp()
        switch_dbuser('librarian')
        self.store = IStore(LibraryFileContent)
        self.content_id = db.Library().add('deadbeef', 1234, 'abababab', 'ba')
        self.file_content = self._getTestFileContent()
        transaction.commit()

    def _getTestFileContent(self):
        """Return the file content object that created."""
        return self.store.find(LibraryFileContent, id=self.content_id).one()

    def test_getAlias(self):
        # Library.getAlias() returns the LibrarayFileAlias for a given
        # LibrarayFileAlias ID.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        self.assertEqual(1, alias.id)

    def test_getAlias_no_such_record(self):
        # Library.getAlias() raises a LookupError, if no record with
        # the given ID exists.
        library = db.Library(restricted=False)
        self.assertRaises(LookupError, library.getAlias, -1, None, '/')

    def test_getAlias_content_is_null(self):
        # Library.getAlias() raises a LookupError, if no content
        # record for the given alias exists.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        self.assertRaises(LookupError, library.getAlias, 1, None, '/')

    def test_getAlias_content_is_none(self):
        # Library.getAlias() raises a LookupError, if the matching
        # record does not reference any LibraryFileContent record.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        self.assertRaises(LookupError, library.getAlias, 1, None, '/')

    def test_getAlias_content_wrong_library(self):
        # Library.getAlias() raises a LookupError, if a restricted
        # library looks up a unrestricted LibraryFileAlias and
        # vice versa.
        restricted_library = db.Library(restricted=True)
        self.assertRaises(
            LookupError, restricted_library.getAlias, 1, None, '/')

        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True
        self.assertRaises(
            LookupError, unrestricted_library.getAlias, 1, None, '/')

    def setUpAuthServer(self):
        authserver = FakeAuthServer()
        authserver_listener = reactor.listenTCP(0, server.Site(authserver))
        self.addCleanup(authserver_listener.stopListening)
        authserver_port = authserver_listener.getHost().port
        authserver_url = 'http://localhost:%d/' % authserver_port
        self.pushConfig('librarian', authentication_endpoint=authserver_url)
        return authserver

    @defer.inlineCallbacks
    def test_getAlias_with_macaroon(self):
        # Library.getAlias() uses the authserver to verify macaroons.
        authserver = self.setUpAuthServer()
        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True
        transaction.commit()
        restricted_library = db.Library(restricted=True)
        macaroon = Macaroon()
        with ExpectedException(LookupError):
            yield deferToThread(restricted_library.getAlias, 1, macaroon, '/')
        authserver.registerMacaroon(macaroon, 1)
        alias = yield deferToThread(
            restricted_library.getAlias, 1, macaroon, '/')
        self.assertEqual(1, alias.id)

    @defer.inlineCallbacks
    def test_getAlias_with_wrong_macaroon(self):
        # A macaroon for a different LFA doesn't work.
        authserver = self.setUpAuthServer()
        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True
        transaction.commit()
        macaroon = Macaroon()
        authserver.registerMacaroon(macaroon, 2)
        restricted_library = db.Library(restricted=True)
        with ExpectedException(LookupError):
            yield deferToThread(restricted_library.getAlias, 1, macaroon, '/')

    @defer.inlineCallbacks
    def test_getAlias_with_macaroon_timeout(self):
        # The authserver call is cancelled after a timeout period.
        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True
        transaction.commit()
        macaroon = Macaroon()
        restricted_library = db.Library(restricted=True)
        self.useFixture(MockPatchObject(
            restricted_library._authserver, 'callRemote',
            return_value=defer.Deferred()))
        # XXX cjwatson 2018-11-01: We should use a Clock instead, but I had
        # trouble getting that working in conjunction with deferToThread.
        self.pushConfig('librarian', authentication_timeout=1)
        with ExpectedException(defer.CancelledError):
            yield deferToThread(restricted_library.getAlias, 1, macaroon, '/')

    def test_getAliases(self):
        # Library.getAliases() returns a sequence
        # [(LFA.id, LFA.filename, LFA.mimetype), ...] where LFA are
        # LibrarayFileAlias records having the given LibraryFileContent
        # ID.
        library = db.Library(restricted=False)
        aliases = library.getAliases(1)
        expected_aliases = [
            (1, u'netapplet-1.0.0.tar.gz', u'application/x-gtar'),
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

    def test_getAliases_content_is_none(self):
        # Library.getAliases() does not return records which do not
        # reference any LibraryFileContent record.
        library = db.Library(restricted=False)
        alias = library.getAlias(1, None, '/')
        alias.content = None
        aliases = library.getAliases(1)
        expected_aliases = [
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

    def test_getAliases_content_wrong_library(self):
        # Library.getAliases() does not return data from restriceded
        # LibrarayFileAlias records when called from a unrestricted
        # library and vice versa.
        unrestricted_library = db.Library(restricted=False)
        alias = unrestricted_library.getAlias(1, None, '/')
        alias.restricted = True

        aliases = unrestricted_library.getAliases(1)
        expected_aliases = [
            (2, u'netapplet_1.0.0.orig.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)

        restricted_library = db.Library(restricted=True)
        aliases = restricted_library.getAliases(1)
        expected_aliases = [
            (1, u'netapplet-1.0.0.tar.gz', u'application/x-gtar'),
            ]
        self.assertEqual(expected_aliases, aliases)
