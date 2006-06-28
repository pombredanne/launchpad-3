# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""

import unittest
import logging
import os

import transaction
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctest import DocFileSuite
from zope.component import getUtility
import sqlos.connection

from canonical.config import config
from canonical.functional import FunctionalDocFileSuite
from canonical.testing.layers import (
        LaunchpadZopeless, LaunchpadFunctional, Librarian, Database, Zopeless,
        ZopelessCA
        )
from canonical.launchpad.ftests.harness import (
        LaunchpadTestSetup, LaunchpadZopelessTestSetup,
        _disconnect_sqlos, _reconnect_sqlos
        )
from canonical.launchpad.interfaces import ILaunchBag, IOpenLaunchBag
from canonical.launchpad.mail import stub
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.database.sqlbase import flush_database_updates

here = os.path.dirname(os.path.realpath(__file__))

default_optionflags = REPORT_NDIFF | NORMALIZE_WHITESPACE | ELLIPSIS

def setGlobs(test):
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility
    test.globs['transaction'] = transaction
    test.globs['flush_database_updates'] = flush_database_updates

def setUp(test):
    #sqlos.connection.connCache = {}
    #LaunchpadTestSetup().setUp()
    #_reconnect_sqlos()
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)

def tearDown(test):
    logout()
    #getUtility(IOpenLaunchBag).clear()
    #_disconnect_sqlos()
    #sqlos.connection.connCache = {}
    #LaunchpadTestSetup().tearDown()
    #stub.test_emails = []

def poExportSetUp(test):
    LaunchpadZopelessTestSetup(dbuser='poexport').setUp()
    setUp(test)

def poExportTearDown(test):
    tearDown(test)
    LaunchpadZopelessTestSetup().tearDown()

def uploaderSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='uploader').setUp()
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)

def uploaderTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def importdSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='importd').setUp()
    setUp(test)

def importdTearDown(test):
    tearDown(test)
    LaunchpadZopelessTestSetup().tearDown()

def supportTrackerSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser=config.tickettracker.dbuser).setUp()
    setGlobs(test)
    login(ANONYMOUS)

def supportTrackerTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def karmaUpdaterTearDown(test):
    # We can't detect db changes made by the subprocess
    LaunchpadTestSetup().force_dirty_database()

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

def LayeredDocFileSuite(*args, **kw):
    '''Create a DocFileSuite with a layer.'''
    layer = kw['layer']
    del kw['layer']
    suite = DocFileSuite(*args, **kw)
    suite.layer = layer
    return suite


# Files that have special needs can construct their own suite
# XXX: Note the wierd path differences between specifying a DocFileSuite
# and a FunctionalDocFileSuite. No idea why there are differences between
# the relative paths, or how to fix this -- StuartBishop 20060228
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'testing.txt': DocFileSuite(
            '../doc/testing.txt', optionflags=default_optionflags
            ),

    'remove-upstream-translations-script.txt': FunctionalDocFileSuite(
            'launchpad/doc/remove-upstream-translations-script.txt',
            optionflags=default_optionflags, layer=LaunchpadFunctional,
            setUp=setUp, tearDown=tearDown
            ),

    # And these tests want minimal environments too.
    'poparser.txt': DocFileSuite(
            '../doc/poparser.txt', optionflags=default_optionflags
            ),

    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distrorelease-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
    'poexport.txt': LayeredDocFileSuite(
            '../doc/poexport.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown,
            optionflags=default_optionflags, layer=Zopeless
            ),
    'poexport-template-tarball.txt': LayeredDocFileSuite(
            '../doc/poexport-template-tarball.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown, layer=Zopeless
            ),
    'po_export_queue.txt': FunctionalDocFileSuite(
            'launchpad/doc/po_export_queue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'librarian.txt': FunctionalDocFileSuite(
            'launchpad/doc/librarian.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'message.txt': FunctionalDocFileSuite(
            'launchpad/doc/message.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'cve-update.txt': FunctionalDocFileSuite(
            'launchpad/doc/cve-update.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'nascentupload.txt': FunctionalDocFileSuite(
            'launchpad/doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown,
            layer=LaunchpadFunctional
            ),
    'revision.txt': LayeredDocFileSuite(
            '../doc/revision.txt',
            setUp=importdSetUp, tearDown=importdTearDown,
            optionflags=default_optionflags, layer=Zopeless),
    'support-tracker-emailinterface.txt': FunctionalDocFileSuite(
            'launchpad/doc/support-tracker-emailinterface.txt',
            setUp=supportTrackerSetUp, tearDown=supportTrackerTearDown,
            layer=ZopelessCA),
    'karmaupdater.txt': FunctionalDocFileSuite(
            'launchpad/doc/karmaupdater.txt',
            setUp=setGlobs, tearDown=karmaUpdaterTearDown,
            optionflags=default_optionflags, layer=Database,
            stdout_logging_level=logging.WARNING
            ),
    'bugnotification-sending.txt': LayeredDocFileSuite(
            '../doc/bugnotification-sending.txt',
            optionflags=default_optionflags,
            layer=Zopeless, setUp=bugNotificationSendingSetup,
            tearDown=bugNotificationSendingTearDown),
    'bugmail-headers.txt': LayeredDocFileSuite(
            '../doc/bugmail-headers.txt',
            optionflags=default_optionflags, layer=Zopeless,
            setUp=bugNotificationSendingSetup,
            tearDown=bugNotificationSendingTearDown),
    'branch-status-client.txt': FunctionalDocFileSuite(
            'launchpad/doc/branch-status-client.txt',
            setUp=branchStatusSetUp, tearDown=branchStatusTearDown,
            layer=Zopeless),
    'translationimportqueue.txt': FunctionalDocFileSuite(
            'launchpad/doc/translationimportqueue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'pofile-pages.txt': FunctionalDocFileSuite(
            'launchpad/doc/pofile-pages.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'rosetta-karma.txt': FunctionalDocFileSuite(
            'launchpad/doc/rosetta-karma.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional
            ),
    'incomingmail.txt': FunctionalDocFileSuite(
            'launchpad/doc/incomingmail.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional,
            stdout_logging_level=logging.WARNING
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
        path = os.path.join('launchpad/doc/', filename)
        one_test = FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctional,
            optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
