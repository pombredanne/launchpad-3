# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""

import unittest
import os
from canonical.functional import FunctionalDocFileSuite
import sqlos.connection
from canonical.launchpad.ftests.harness import \
        LaunchpadTestSetup, LaunchpadZopelessTestSetup, \
        _disconnect_sqlos, _reconnect_sqlos
from zope.testing.doctest import DocFileSuite
from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag, IOpenLaunchBag
from canonical.launchpad.mail import stub
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.librarian.ftests.harness import LibrarianTestSetup

here = os.path.dirname(os.path.realpath(__file__))

def setGlobs(test):
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility

def setUp(test):
    sqlos.connection.connCache = {}
    LaunchpadTestSetup().setUp()
    _reconnect_sqlos()
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)

def tearDown(test):
    getUtility(IOpenLaunchBag).clear()
    _disconnect_sqlos()
    sqlos.connection.connCache = {}
    LaunchpadTestSetup().tearDown()
    stub.test_emails = []

def poExportSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='poexport').setUp()
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)

def poExportTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def uploaderSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='uploader').setUp()
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)

def uploaderTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def librarianSetUp(test):
    setUp(test)
    LibrarianTestSetup().setUp()

def librarianTearDown(test):
    LibrarianTestSetup().tearDown()
    tearDown(test)

# Files that have special needs can construct their own suite
special = {

    # No setup or teardown at all, since it is demonstrating these features.
    'testing.txt': DocFileSuite('../doc/testing.txt'),

    # And these tests want minimal environments too.
    'enumcol.txt': DocFileSuite('../doc/enumcol.txt'),
    'poparser.txt': DocFileSuite('../doc/poparser.txt'),

    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distrorelease-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
    'poexport.txt': FunctionalDocFileSuite(
            '../doc/poexport.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown
            ),
    'poexport-template-tarball.txt': FunctionalDocFileSuite(
            '../doc/poexport-template-tarball.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown
            ),
    'librarian.txt': FunctionalDocFileSuite(
            '../doc/librarian.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'message.txt': FunctionalDocFileSuite(
            '../doc/message.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'cve-update.txt': FunctionalDocFileSuite(
            '../doc/cve-update.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'nascentupload.txt': FunctionalDocFileSuite(
            '../doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown
            ),
    }

def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    keys = special.keys()
    keys.sort()
    for key in keys:
        special_suite = special[key]
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
            os.path.normpath(os.path.join(here, '..', 'doc'))
            )

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                    and filename not in special
                 ]
    # Sort the list to give a predictable order.  We do this because when
    # tests interfere with each other, the varying orderings that os.listdir
    # gives on different people's systems make reproducing and debugging
    # problems difficult.  Ideally the test harness would stop the tests from
    # being able to interfere with each other in the first place.
    #   -- Andrew Bennetts, 2005-03-01.
    filenames.sort()
    for filename in filenames:
        path = os.path.join('../doc/', filename)
        suite.addTest(FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown
            ))

    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
