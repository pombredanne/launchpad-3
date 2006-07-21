# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""

import unittest
import logging
import os

from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS
from zope.security.management import (
    endInteraction, newInteraction, queryInteraction)
import sqlos.connection

from canonical.config import config
from canonical.functional import (
        FunctionalDocFileSuite, SystemDoctestLayer, ZopelessLayer,
        )
from canonical.launchpad.ftests.harness import \
        LaunchpadTestSetup, LaunchpadZopelessTestSetup, \
        _disconnect_sqlos, _reconnect_sqlos
from zope.testing.doctest import DocFileSuite
from zope.component import getUtility
from canonical.launchpad.interfaces import ILaunchBag, IOpenLaunchBag
from canonical.launchpad.mail import stub
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.librarian.ftests.harness import LibrarianTestSetup
from canonical.authserver.ftests.harness import AuthserverTacTestSetup

here = os.path.dirname(os.path.realpath(__file__))

default_optionflags = REPORT_NDIFF | NORMALIZE_WHITESPACE | ELLIPSIS


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
    login(ANONYMOUS)


def tearDown(test):
    # Make sure there is an interaction in order for the getUtility call
    # to work.
    if not queryInteraction():
        newInteraction()
    getUtility(IOpenLaunchBag).clear()
    endInteraction()
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

def importdSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='importd').setUp()
    setGlobs(test)

def importdTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def supportTrackerSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser=config.tickettracker.dbuser).setUp()
    LibrarianTestSetup().setUp()
    setGlobs(test)
    login(ANONYMOUS)

def supportTrackerTearDown(test):
    LibrarianTestSetup().tearDown()
    LaunchpadZopelessTestSetup().tearDown()

def peopleKarmaTearDown(test):
    # We can't detect db changes made by the subprocess
    LaunchpadTestSetup().force_dirty_database()
    tearDown(test)

def branchStatusSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='launchpad').setUp()
    test._authserver = AuthserverTacTestSetup()
    test._authserver.setUp()

def branchStatusTearDown(test):
    test._authserver.tearDown()
    LaunchpadZopelessTestSetup().tearDown()

def bugNotificationSendingSetup(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(
        dbuser=config.malone.bugnotification_dbuser).setUp()
    setGlobs(test)
    login(ANONYMOUS)

def bugNotificationSendingTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()


# Files that have special needs can construct their own suite
# XXX: Note the wierd path differences between specifying a DocFileSuite
# and a FunctionalDocFileSuite. No idea why there are differences between
# the relative paths, or how to fix this -- StuartBishop 20060228
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'testing.txt': DocFileSuite(
            '../doc/testing.txt', optionflags=default_optionflags
            ),

    # We are going to setup and teardown several times inside this test, we
    # don't need to execute it automatically here.
    'remove-upstream-translations-script.txt': DocFileSuite(
            '../doc/remove-upstream-translations-script.txt',
            optionflags=default_optionflags
            ),

    # And these tests want minimal environments too.
    'enumcol.txt': DocFileSuite('../doc/enumcol.txt'),
    'poparser.txt': DocFileSuite(
            '../doc/poparser.txt', optionflags=default_optionflags
            ),

    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distrorelease-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
    'poexport.txt': DocFileSuite(
            '../doc/poexport.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown,
            optionflags=default_optionflags
            ),
    'poexport-template-tarball.txt': DocFileSuite(
            '../doc/poexport-template-tarball.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown
            ),
    'po_export_queue.txt': FunctionalDocFileSuite(
            'launchpad/doc/po_export_queue.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'librarian.txt': FunctionalDocFileSuite(
            'launchpad/doc/librarian.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'message.txt': FunctionalDocFileSuite(
            'launchpad/doc/message.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'cve-update.txt': FunctionalDocFileSuite(
            'launchpad/doc/cve-update.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'nascentupload.txt': FunctionalDocFileSuite(
            'launchpad/doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown
            ),
    'revision.txt': DocFileSuite(
            '../doc/revision.txt',
            setUp=importdSetUp, tearDown=importdTearDown,
            optionflags=default_optionflags),
    'support-tracker-emailinterface.txt': FunctionalDocFileSuite(
            'launchpad/doc/support-tracker-emailinterface.txt',
            setUp=supportTrackerSetUp, tearDown=supportTrackerTearDown),
    'person-karma.txt': FunctionalDocFileSuite(
            'launchpad/doc/person-karma.txt',
            setUp=setUp, tearDown=peopleKarmaTearDown,
            optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            ),
    'bugnotification-sending.txt': DocFileSuite(
            '../doc/bugnotification-sending.txt',
            optionflags=default_optionflags,
            setUp=bugNotificationSendingSetup,
            tearDown=bugNotificationSendingTearDown),
    'bugmail-headers.txt': DocFileSuite(
            '../doc/bugmail-headers.txt',
            optionflags=default_optionflags,
            setUp=bugNotificationSendingSetup,
            tearDown=bugNotificationSendingTearDown),
    'branch-status-client.txt': FunctionalDocFileSuite(
            'launchpad/doc/branch-status-client.txt',
            setUp=branchStatusSetUp, tearDown=branchStatusTearDown),
    'translationimportqueue.txt': FunctionalDocFileSuite(
            'launchpad/doc/translationimportqueue.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'pofile-pages.txt': FunctionalDocFileSuite(
            'launchpad/doc/pofile-pages.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    'rosetta-karma.txt': FunctionalDocFileSuite(
            'launchpad/doc/rosetta-karma.txt',
            setUp=librarianSetUp, tearDown=librarianTearDown
            ),
    }

special['poexport.txt'].layer = ZopelessLayer
special['support-tracker-emailinterface.txt'].layer = ZopelessLayer
special['branch-status-client.txt'].layer = ZopelessLayer
special['bugnotification-sending.txt'].layer = ZopelessLayer
special['bugmail-headers.txt'].layer = ZopelessLayer
special['revision.txt'].layer = ZopelessLayer

def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    keys = special.keys()
    keys.sort()
    for key in keys:
        special_suite = special[key]
        if getattr(special_suite, 'layer', None) is None:
            special_suite.layer = SystemDoctestLayer
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
        path = os.path.join('launchpad/doc/', filename)
        one_test = FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
