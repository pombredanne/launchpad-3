# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""

import unittest
import logging
import os

import transaction

from zope.component import getUtility
from zope.security.management import getSecurityPolicy, setSecurityPolicy
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctest import DocFileSuite
import sqlos.connection

from canonical.authserver.ftests.harness import AuthserverTacTestSetup
from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.functional import FunctionalDocFileSuite
from canonical.launchpad.ftests import login, ANONYMOUS, logout
from canonical.launchpad.ftests.harness import (
        LaunchpadTestSetup, LaunchpadZopelessTestSetup,
        _disconnect_sqlos, _reconnect_sqlos
        )
from canonical.launchpad.interfaces import ILaunchBag, IOpenLaunchBag
from canonical.launchpad.mail import stub
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.testing import (
        LaunchpadZopelessLayer, LaunchpadFunctionalLayer, LibrarianLayer,
        DatabaseLayer, ZopelessLayer, FunctionalLayer, LaunchpadLayer,
        )

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
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)


def tearDown(test):
    logout()

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

def builddmasterSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser=config.builddmaster.dbuser).setUp()
    setGlobs(test)
    login(ANONYMOUS)

def builddmasterTearDown(test):
    LaunchpadZopelessTestSetup().tearDown()

def importdSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(dbuser='importd').setUp()
    setUp(test)

def importdTearDown(test):
    tearDown(test)
    LaunchpadZopelessTestSetup().tearDown()

def supportTrackerSetUp(test):
    setGlobs(test)
    # The Zopeless environment usually runs using the PermissivePolicy
    # but the process-mail.py script in which the tested code runs
    # use the regular web policy.
    test.old_security_policy = getSecurityPolicy()
    setSecurityPolicy(LaunchpadSecurityPolicy)

def supportTrackerTearDown(test):
    setSecurityPolicy(test.old_security_policy)

def peopleKarmaTearDown(test):
    # We can't detect db changes made by the subprocess
    LaunchpadTestSetup().force_dirty_database()

def branchStatusSetUp(test):
    test._authserver = AuthserverTacTestSetup()
    test._authserver.setUp()

def branchStatusTearDown(test):
    test._authserver.tearDown()

def bugNotificationSendingSetUp(test):
    sqlos.connection.connCache = {}
    # XXX: Note that the DB is already setup by the layer - this call just
    # reconnects us as a different user. This should use a more obvious API.
    # Note that the layer still tears things down as necessary
    # -- StuartBishop 20060712
    LaunchpadZopelessTestSetup(
        dbuser=config.malone.bugnotification_dbuser).setUp()
    setGlobs(test)
    login(ANONYMOUS)

def bugNotificationSendingTearDown(test):
    logout()
    LaunchpadZopelessTestSetup().tearDown()

def statisticianSetUp(test):
    sqlos.connection.connCache = {}
    LaunchpadZopelessTestSetup(
        dbuser=config.statistician.dbuser).setUp()
    setGlobs(test)
    login(ANONYMOUS)

def statisticianTearDown(test):
    logout()
    LaunchpadZopelessTestSetup().tearDown()

def LayeredDocFileSuite(*args, **kw):
    '''Create a DocFileSuite with a layer.'''
    layer = kw.pop('layer')
    suite = DocFileSuite(*args, **kw)
    suite.layer = layer
    return suite


# Files that have special needs can construct their own suite
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'old-testing.txt': LayeredDocFileSuite(
            '../doc/old-testing.txt', optionflags=default_optionflags,
            layer=FunctionalLayer
            ),

    'remove-upstream-translations-script.txt': DocFileSuite(
            '../doc/remove-upstream-translations-script.txt',
            optionflags=default_optionflags, setUp=setGlobs
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
            optionflags=default_optionflags, layer=ZopelessLayer
            ),
    'poexport-template-tarball.txt': LayeredDocFileSuite(
            '../doc/poexport-template-tarball.txt',
            setUp=poExportSetUp, tearDown=poExportTearDown, layer=ZopelessLayer
            ),
    'poexport-queue.txt': FunctionalDocFileSuite(
            '../doc/poexport-queue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'librarian.txt': FunctionalDocFileSuite(
            '../doc/librarian.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'message.txt': FunctionalDocFileSuite(
            '../doc/message.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'cve-update.txt': FunctionalDocFileSuite(
            '../doc/cve-update.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'nascentupload.txt': FunctionalDocFileSuite(
            '../doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'build-notification.txt': LayeredDocFileSuite(
            '../doc/build-notification.txt',
            setUp=builddmasterSetUp, tearDown=builddmasterTearDown,
            layer=ZopelessLayer, optionflags=default_optionflags
            ),
    'revision.txt': LayeredDocFileSuite(
            '../doc/revision.txt',
            setUp=importdSetUp, tearDown=importdTearDown,
            optionflags=default_optionflags, layer=ZopelessLayer
            ),
    'support-tracker-emailinterface.txt': LayeredDocFileSuite(
            '../doc/support-tracker-emailinterface.txt',
            setUp=supportTrackerSetUp, tearDown=supportTrackerTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'person-karma.txt': FunctionalDocFileSuite(
            '../doc/person-karma.txt',
            setUp=setUp, tearDown=peopleKarmaTearDown,
            optionflags=default_optionflags, layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            ),
    'bugnotification-sending.txt': LayeredDocFileSuite(
            '../doc/bugnotification-sending.txt',
            optionflags=default_optionflags,
            layer=ZopelessLayer, setUp=bugNotificationSendingSetUp,
            tearDown=bugNotificationSendingTearDown
            ),
    'bugmail-headers.txt': LayeredDocFileSuite(
            '../doc/bugmail-headers.txt',
            optionflags=default_optionflags, layer=ZopelessLayer,
            setUp=bugNotificationSendingSetUp,
            tearDown=bugNotificationSendingTearDown),
    'branch-status-client.txt': LayeredDocFileSuite(
            '../doc/branch-status-client.txt',
            setUp=branchStatusSetUp, tearDown=branchStatusTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'translationimportqueue.txt': FunctionalDocFileSuite(
            '../doc/translationimportqueue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'pofile-pages.txt': FunctionalDocFileSuite(
            '../doc/pofile-pages.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'rosetta-karma.txt': FunctionalDocFileSuite(
            '../doc/rosetta-karma.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'incomingmail.txt': FunctionalDocFileSuite(
            '../doc/incomingmail.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            ),
    'launchpadform.txt': FunctionalDocFileSuite(
            '../doc/launchpadform.txt',
            setUp=setUp, tearDown=tearDown, optionflags=default_optionflags,
            layer=FunctionalLayer
            ),
    'launchpadformharness.txt': FunctionalDocFileSuite(
            '../doc/launchpadformharness.txt',
            setUp=setUp, tearDown=tearDown, optionflags=default_optionflags,
            layer=FunctionalLayer
            ),
    'bug-export.txt': LayeredDocFileSuite(
            '../doc/bug-export.txt',
            setUp=setUp, tearDown=tearDown, optionflags=default_optionflags,
            layer=LaunchpadZopelessLayer
            ),
    'uri.txt': FunctionalDocFileSuite(
            '../doc/uri.txt',
            setUp=setUp, tearDown=tearDown, optionflags=default_optionflags,
            layer=FunctionalLayer
            ),
    'package-cache.txt': LayeredDocFileSuite(
            '../doc/package-cache.txt',
            setUp=statisticianSetUp, tearDown=statisticianTearDown,
            optionflags=default_optionflags, layer=ZopelessLayer
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
        one_test = FunctionalDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer, optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite

if __name__ == '__main__':
    unittest.main(test_suite())
