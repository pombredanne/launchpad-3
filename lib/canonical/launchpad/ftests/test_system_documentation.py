# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""
# pylint: disable-msg=C0103

import logging
import os
import unittest

from zope.component import getUtility
from zope.security.management import setSecurityPolicy

from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.config import config
from canonical.database.sqlbase import (
    commit, flush_database_updates, ISOLATION_LEVEL_READ_COMMITTED)
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.ftests import mailinglists_helper
from canonical.launchpad.ftests.bug import (
    create_old_bug, summarize_bugtasks, sync_bugtasks)
from canonical.launchpad.interfaces import (
    CreateBugParams, IBugTaskSet, IDistributionSet, ILanguageSet,
    IPersonSet)
from canonical.launchpad.testing import browser
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, setGlobs, tearDown)
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.tests import test_notifications
from canonical.testing import (
    AppServerLayer, DatabaseLayer, FunctionalLayer, GoogleServiceLayer,
    LaunchpadFunctionalLayer, LaunchpadZopelessLayer)


here = os.path.dirname(os.path.realpath(__file__))


def checkwatchesSetUp(test):
    """Setup the check watches script tests."""
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser(config.checkwatches.dbuser)

def poExportSetUp(test):
    """Setup the PO export script tests."""
    LaunchpadZopelessLayer.switchDbUser('poexport')
    setUp(test)

def poExportTearDown(test):
    """Tear down the PO export script tests."""
    # XXX sinzui 2007-11-14:
    # This function is not needed. The test should be switched to tearDown.
    tearDown(test)

def uploaderSetUp(test):
    """setup the package uploader script tests."""
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser('uploader')

def uploaderTearDown(test):
    """Tear down the package uploader script tests."""
    # XXX sinzui 2007-11-14:
    # This function is not needed. The test should be switched to tearDown.
    tearDown(test)

def builddmasterSetUp(test):
    """Setup the connection for the build master tests."""
    test_dbuser = config.builddmaster.dbuser
    test.globs['test_dbuser'] = test_dbuser
    LaunchpadZopelessLayer.alterConnection(
        dbuser=test_dbuser, isolation=ISOLATION_LEVEL_READ_COMMITTED)
    setGlobs(test)

def branchscannerSetUp(test):
    """Setup the user for the branch scanner tests."""
    LaunchpadZopelessLayer.switchDbUser('branchscanner')
    setUp(test)

def branchscannerTearDown(test):
    """Tear down the branch scanner tests."""
    # XXX sinzui 2007-11-14:
    # This function is not needed. The test should be switched to tearDown.
    tearDown(test)


def peopleKarmaTearDown(test):
    """Restore the database after testing karma."""
    # We can't detect db changes made by the subprocess (yet).
    DatabaseLayer.force_dirty_database()
    tearDown(test)

def branchStatusSetUp(test):
    test._authserver = AuthserverTacTestSetup()
    test._authserver.setUp()

def branchStatusTearDown(test):
    test._authserver.tearDown()

def bugNotificationSendingSetUp(test):
    LaunchpadZopelessLayer.switchDbUser(config.malone.bugnotification_dbuser)
    setUp(test)

def bugNotificationSendingTearDown(test):
    tearDown(test)

def statisticianSetUp(test):
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser(config.statistician.dbuser)

def statisticianTearDown(test):
    tearDown(test)

def distroseriesqueueSetUp(test):
    setUp(test)
    # The test requires that the umask be set to 022, and in fact this comment
    # was made in irc on 13-Apr-2007:
    #
    # (04:29:18 PM) kiko: barry, cprov says that the local umask is controlled
    # enough for us to rely on it
    #
    # Setting it here reproduces the environment that the doctest expects.
    # Save the old umask so we can reset it in the tearDown().
    test.old_umask = os.umask(022)

def distroseriesqueueTearDown(test):
    os.umask(test.old_umask)
    tearDown(test)

def uploadQueueSetUp(test):
    test_dbuser = config.uploadqueue.dbuser
    LaunchpadZopelessLayer.switchDbUser(test_dbuser)
    setUp(test)
    test.globs['test_dbuser'] = test_dbuser

def uploaderBugsSetUp(test):
    """Set up a test suite using the 'uploader' db user.

    Some aspects of the bug tracker are being used by the Soyuz uploader.
    In order to test that these functions work as expected from the uploader,
    we run them using the same db user used by the uploader.
    """
    test_dbuser = config.uploader.dbuser
    LaunchpadZopelessLayer.switchDbUser(test_dbuser)
    setUp(test)
    test.globs['test_dbuser'] = test_dbuser

def uploaderBugsTearDown(test):
    logout()

def uploadQueueTearDown(test):
    logout()

def noPrivSetUp(test):
    """Set up a test logged in as no-priv."""
    setUp(test)
    login('no-priv@canonical.com')

def _createUbuntuBugTaskLinkedToQuestion():
    """Get the id of an Ubuntu bugtask linked to a question.

    The Ubuntu team is set as the answer contact for Ubuntu, and no-priv
    is used as the submitter..
    """
    login('test@canonical.com')
    sample_person = getUtility(IPersonSet).getByEmail('test@canonical.com')
    ubuntu_team = getUtility(IPersonSet).getByName('ubuntu-team')
    ubuntu_team.addLanguage(getUtility(ILanguageSet)['en'])
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    ubuntu.addAnswerContact(ubuntu_team)
    ubuntu_question = ubuntu.newQuestion(
        sample_person, "Can't install Ubuntu",
        "I insert the install CD in the CD-ROM drive, but it won't boot.")
    no_priv = getUtility(IPersonSet).getByEmail('no-priv@canonical.com')
    params = CreateBugParams(
        owner=no_priv, title="Installer fails on a Mac PPC",
        comment=ubuntu_question.description)
    bug = ubuntu.createBug(params)
    ubuntu_question.linkBug(bug)
    [ubuntu_bugtask] = bug.bugtasks
    login(ANONYMOUS)
    # Remove the notifcations for the newly created question.
    notifications = pop_notifications()
    return ubuntu_bugtask.id

def bugLinkedToQuestionSetUp(test):
    """Setup the question and linked bug for testing."""
    def get_bugtask_linked_to_question():
        return getUtility(IBugTaskSet).get(bugtask_id)
    setUp(test)
    bugtask_id = _createUbuntuBugTaskLinkedToQuestion()
    test.globs['get_bugtask_linked_to_question'] = (
        get_bugtask_linked_to_question)
    # Log in here, since we don't want to set up an non-anonymous
    # interaction in the test.
    login('no-priv@canonical.com')


def bugtaskExpirationSetUp(test):
    """Setup globs for bug expiration."""
    setUp(test)
    test.globs['create_old_bug'] = create_old_bug
    test.globs['summarize_bugtasks'] = summarize_bugtasks
    test.globs['sync_bugtasks'] = sync_bugtasks
    test.globs['commit'] = commit
    login('test@canonical.com')


def uploaderBugLinkedToQuestionSetUp(test):
    LaunchpadZopelessLayer.switchDbUser('launchpad')
    bugLinkedToQuestionSetUp(test)
    LaunchpadZopelessLayer.commit()
    uploaderSetUp(test)
    login(ANONYMOUS)

def uploadQueueBugLinkedToQuestionSetUp(test):
    LaunchpadZopelessLayer.switchDbUser('launchpad')
    bugLinkedToQuestionSetUp(test)
    LaunchpadZopelessLayer.commit()
    uploadQueueSetUp(test)
    login(ANONYMOUS)

def translationMessageDestroySetUp(test):
    """Set up the TranslationMessage.destroySelf() test."""
    LaunchpadZopelessLayer.switchDbUser('rosettaadmin')
    setUp(test)

def translationMessageDestroyTearDown(test):
    """Tear down the TranslationMessage.destroySelf() test."""
    tearDown(test)

def manageChrootSetup(test):
    """Set up the manage-chroot.txt test."""
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser("fiera")


# XXX BarryWarsaw 15-Aug-2007: See bug 132784 as a placeholder for improving
# the harness for the mailinglist-xmlrpc.txt tests, or improving things so
# that all this cruft isn't necessary.

def mailingListXMLRPCInternalSetUp(test):
    setUp(test)
    # Use the direct API view instance, not retrieved through the component
    # architecture.  Don't use ServerProxy.  We do this because it's easier to
    # debug because when things go horribly wrong, you see the errors on
    # stdout instead of in an OOPS report living in some log file somewhere.
    from canonical.launchpad.xmlrpc import MailingListAPIView
    class ImpedenceMatchingView(MailingListAPIView):
        @mailinglists_helper.fault_catcher
        def getPendingActions(self):
            return super(ImpedenceMatchingView, self).getPendingActions()
        @mailinglists_helper.fault_catcher
        def reportStatus(self, statuses):
            return super(ImpedenceMatchingView, self).reportStatus(statuses)
        @mailinglists_helper.fault_catcher
        def getMembershipInformation(self, teams):
            return super(
                ImpedenceMatchingView, self).getMembershipInformation(teams)
        @mailinglists_helper.fault_catcher
        def isLaunchpadMember(self, address):
            return super(ImpedenceMatchingView, self).isLaunchpadMember(
                address)
    # Expose in the doctest's globals, the view as the thing with the
    # IMailingListAPI interface.  Also expose the helper functions.
    mailinglist_api = ImpedenceMatchingView(context=None, request=None)
    test.globs['mailinglist_api'] = mailinglist_api
    # Expose different commit() functions to handle the 'external' case below
    # where there is more than one connection.  The 'internal' case here has
    # just one coneection so the flush is all we need.
    test.globs['commit'] = flush_database_updates


def mailingListXMLRPCExternalSetUp(test):
    setUp(test)
    # Use a real XMLRPC server proxy so that the same test is run through the
    # full security machinery.  This is more representative of the real-world,
    # but more difficult to debug.
    from canonical.functional import XMLRPCTestTransport
    from xmlrpclib import ServerProxy
    mailinglist_api = ServerProxy(
        'http://xmlrpc-private.launchpad.dev:8087/mailinglists/',
        transport=XMLRPCTestTransport())
    test.globs['mailinglist_api'] = mailinglist_api
    # See above; right now this is the same for both the internal and external
    # tests, but if we're able to resolve the big XXX above the
    # mailinglist-xmlrpc.txt-external declaration below, I suspect that these
    # two globals will end up being different functions.
    test.globs['mailinglist_api'] = mailinglist_api
    test.globs['commit'] = flush_database_updates


def zopelessLaunchpadSecuritySetUp(test):
    """Set up a LaunchpadZopelessLayer test to use LaunchpadSecurityPolicy.

    To be able to use LaunchpadZopelessLayer.switchDbUser in a test, we need
    to run in the Zopeless environment. The Zopeless environment normally runs
    using the PermissiveSecurityPolicy. If we want the test to cover
    functionality used in the webapp, it needs to use the
    LaunchpadSecurityPolicy.
    """
    setGlobs(test)
    test.old_security_policy = setSecurityPolicy(LaunchpadSecurityPolicy)


def zopelessLaunchpadSecurityTearDown(test):
    setSecurityPolicy(test.old_security_policy)


def hwdbDeviceTablesSetup(test):
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser('hwdb-submission-processor')


# Files that have special needs can construct their own suite
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'old-testing.txt': LayeredDocFileSuite(
            '../doc/old-testing.txt', layer=FunctionalLayer
            ),

    'remove-upstream-translations-script.txt': LayeredDocFileSuite(
            '../doc/remove-upstream-translations-script.txt',
            setUp=setGlobs, stdout_logging=False, layer=None
            ),

    # And this test want minimal environment too.
    'package-relationship.txt': LayeredDocFileSuite(
            '../doc/package-relationship.txt',
            stdout_logging=False, layer=None
            ),

    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distroseries-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
    'poexport-queue.txt': LayeredDocFileSuite(
            '../doc/poexport-queue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'librarian.txt': LayeredDocFileSuite(
            '../doc/librarian.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'message.txt': LayeredDocFileSuite(
            '../doc/message.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'cve-update.txt': LayeredDocFileSuite(
            '../doc/cve-update.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'nascentupload.txt': LayeredDocFileSuite(
            '../doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown,
            layer=LaunchpadZopelessLayer,
            ),
    'build-notification.txt': LayeredDocFileSuite(
            '../doc/build-notification.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer,
            ),
    'buildd-slavescanner.txt': LayeredDocFileSuite(
            '../doc/buildd-slavescanner.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer,
            stdout_logging_level=logging.WARNING
            ),
    'buildd-scoring.txt': LayeredDocFileSuite(
            '../doc/buildd-scoring.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer,
            ),
    'buildd-queuebuilder.txt': LayeredDocFileSuite(
            '../doc/buildd-queuebuilder.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer,
            stdout_logging_level=logging.WARNING
            ),
    'revision.txt': LayeredDocFileSuite(
            '../doc/revision.txt',
            setUp=branchscannerSetUp, tearDown=branchscannerTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'person-karma.txt': LayeredDocFileSuite(
            '../doc/person-karma.txt',
            setUp=setUp, tearDown=peopleKarmaTearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            ),
    'bugnotificationrecipients.txt-uploader': LayeredDocFileSuite(
            '../doc/bugnotificationrecipients.txt',
            setUp=uploaderBugsSetUp,
            tearDown=uploaderBugsTearDown,
            layer=LaunchpadZopelessLayer
            ),
     'bugnotificationrecipients.txt-queued': LayeredDocFileSuite(
            '../doc/bugnotificationrecipients.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bugnotification-sending.txt': LayeredDocFileSuite(
            '../doc/bugnotification-sending.txt',
            layer=LaunchpadZopelessLayer, setUp=bugNotificationSendingSetUp,
            tearDown=bugNotificationSendingTearDown
            ),
    'bugmail-headers.txt': LayeredDocFileSuite(
            '../doc/bugmail-headers.txt',
            layer=LaunchpadZopelessLayer,
            setUp=bugNotificationSendingSetUp,
            tearDown=bugNotificationSendingTearDown),
    'translationimportqueue.txt': LayeredDocFileSuite(
            '../doc/translationimportqueue.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'pofile-pages.txt': LayeredDocFileSuite(
            '../doc/pofile-pages.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'rosetta-karma.txt': LayeredDocFileSuite(
            '../doc/rosetta-karma.txt',
            setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer
            ),
    'launchpadform.txt': LayeredDocFileSuite(
            '../doc/launchpadform.txt',
            setUp=setUp, tearDown=tearDown,
            layer=FunctionalLayer
            ),
    'launchpadformharness.txt': LayeredDocFileSuite(
            '../doc/launchpadformharness.txt',
            setUp=setUp, tearDown=tearDown,
            layer=FunctionalLayer
            ),
    'bug-export.txt': LayeredDocFileSuite(
            '../doc/bug-export.txt',
            setUp=setUp, tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'uri.txt': LayeredDocFileSuite(
            '../doc/uri.txt',
            setUp=setUp, tearDown=tearDown,
            layer=FunctionalLayer
            ),
    'package-cache.txt': LayeredDocFileSuite(
            '../doc/package-cache.txt',
            setUp=statisticianSetUp, tearDown=statisticianTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'distroarchseriesbinarypackage.txt': LayeredDocFileSuite(
            '../doc/distroarchseriesbinarypackage.txt',
            setUp=setUp, tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'script-monitoring.txt': LayeredDocFileSuite(
            '../doc/script-monitoring.txt',
            setUp=setUp, tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'distroseriesqueue-debian-installer.txt': LayeredDocFileSuite(
            '../doc/distroseriesqueue-debian-installer.txt',
            setUp=distroseriesqueueSetUp, tearDown=distroseriesqueueTearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'bug-set-status.txt': LayeredDocFileSuite(
            '../doc/bug-set-status.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bug-set-status.txt-uploader': LayeredDocFileSuite(
            '../doc/bug-set-status.txt',
            setUp=uploaderBugsSetUp,
            tearDown=uploaderBugsTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'closing-bugs-from-changelogs.txt': LayeredDocFileSuite(
            '../doc/closing-bugs-from-changelogs.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'closing-bugs-from-changelogs.txt-uploader': LayeredDocFileSuite(
            '../doc/closing-bugs-from-changelogs.txt',
            setUp=uploaderBugsSetUp,
            tearDown=uploaderBugsTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bugtask-expiration.txt': LayeredDocFileSuite(
            '../doc/bugtask-expiration.txt',
            setUp=bugtaskExpirationSetUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bugmessage.txt': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=noPrivSetUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'bugmessage.txt-queued': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bugmessage.txt-uploader': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=uploaderSetUp,
            tearDown=uploaderTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bugmessage.txt-checkwatches': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=checkwatchesSetUp,
            tearDown=uploaderTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'bug-private-by-default.txt': LayeredDocFileSuite(
            '../doc/bug-private-by-default.txt',
            setUp=setUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'answer-tracker-notifications-linked-bug.txt': LayeredDocFileSuite(
            '../doc/answer-tracker-notifications-linked-bug.txt',
            setUp=bugLinkedToQuestionSetUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'answer-tracker-notifications-linked-bug.txt-uploader':
            LayeredDocFileSuite(
                '../doc/answer-tracker-notifications-linked-bug.txt',
                setUp=uploaderBugLinkedToQuestionSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'answer-tracker-notifications-linked-bug.txt-queued': LayeredDocFileSuite(
            '../doc/answer-tracker-notifications-linked-bug.txt',
            setUp=uploadQueueBugLinkedToQuestionSetUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    'mailinglist-xmlrpc.txt': LayeredDocFileSuite(
            '../doc/mailinglist-xmlrpc.txt',
            setUp=mailingListXMLRPCInternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'mailinglist-xmlrpc.txt-external': LayeredDocFileSuite(
            '../doc/mailinglist-xmlrpc.txt',
            setUp=mailingListXMLRPCExternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            ),
    'checkwatches-cli-switches.txt':
            LayeredDocFileSuite(
                '../doc/checkwatches-cli-switches.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-bug-imports.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-bug-imports.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-bugzilla.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-bugzilla.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-bugzilla-oddities.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-bugzilla-oddities.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-checkwatches.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-checkwatches.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-comment-imports.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-comment-imports.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-comment-pushing.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-comment-pushing.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-debbugs.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-debbugs.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-emailaddress.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-emailaddress.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-mantis-csv.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-mantis-csv.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-mantis.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-mantis.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-python.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-python.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-roundup.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-roundup.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-rt.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-rt.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-sourceforge.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-sourceforge.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-trac.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-trac.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-trac-lp-plugin.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-trac-lp-plugin.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'mailinglist-subscriptions-xmlrpc.txt': LayeredDocFileSuite(
            '../doc/mailinglist-subscriptions-xmlrpc.txt',
            setUp=mailingListXMLRPCInternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'mailinglist-subscriptions-xmlrpc.txt-external': LayeredDocFileSuite(
            '../doc/mailinglist-subscriptions-xmlrpc.txt',
            setUp=mailingListXMLRPCExternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            ),
    'message-holds-xmlrpc.txt': LayeredDocFileSuite(
            '../doc/message-holds-xmlrpc.txt',
            setUp=mailingListXMLRPCInternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer
            ),
    'message-holds-xmlrpc.txt-external': LayeredDocFileSuite(
            '../doc/message-holds-xmlrpc.txt',
            setUp=mailingListXMLRPCExternalSetUp,
            tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            ),
    'codeimport-machine.txt': LayeredDocFileSuite(
            '../doc/codeimport-machine.txt',
            setUp=zopelessLaunchpadSecuritySetUp,
            tearDown=zopelessLaunchpadSecurityTearDown,
            layer=LaunchpadZopelessLayer,
            ),
    # Also run the pillar.txt doctest under the Zopeless layer.
    # This exposed bug #149632.
    'pillar.txt-zopeless': LayeredDocFileSuite(
            '../doc/pillar.txt',
            setUp=setUp, tearDown=tearDown,
            #layer=ExperimentalLaunchpadZopelessLayer
            layer=LaunchpadZopelessLayer
            ),
    'openid-fetcher.txt': LayeredDocFileSuite(
            '../doc/openid-fetcher.txt',
            stdout_logging=False,
            layer=LaunchpadFunctionalLayer
            ),
    'branch-merge-proposals.txt': LayeredDocFileSuite(
            '../doc/branch-merge-proposals.txt',
            setUp=zopelessLaunchpadSecuritySetUp,
            tearDown=zopelessLaunchpadSecurityTearDown,
            layer=LaunchpadZopelessLayer,
            ),
    'soyuz-set-of-uploads.txt': LayeredDocFileSuite(
            '../doc/soyuz-set-of-uploads.txt',
            layer=LaunchpadZopelessLayer,
            ),
    'publishing.txt': LayeredDocFileSuite(
            '../doc/publishing.txt',
            layer=LaunchpadZopelessLayer,
            ),
    'sourcepackagerelease-build-lookup.txt': LayeredDocFileSuite(
            '../doc/sourcepackagerelease-build-lookup.txt',
            layer=LaunchpadZopelessLayer,
            ),
    'notification-text-escape.txt': LayeredDocFileSuite(
            '../doc/notification-text-escape.txt',
            setUp=test_notifications.setUp,
            tearDown=test_notifications.tearDown,
            stdout_logging=False, layer=None
            ),
    'translationmessage-destroy.txt': LayeredDocFileSuite(
            '../doc/translationmessage-destroy.txt',
            setUp=translationMessageDestroySetUp,
            tearDown=translationMessageDestroyTearDown,
            layer=LaunchpadZopelessLayer
            ),
    'manage-chroot.txt': LayeredDocFileSuite(
            '../doc/manage-chroot.txt',
            setUp=manageChrootSetup,
            layer=LaunchpadZopelessLayer,
            ),
    'build-estimated-dispatch-time.txt': LayeredDocFileSuite(
            '../doc/build-estimated-dispatch-time.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer,
            ),
    'hwdb-device-tables.txt': LayeredDocFileSuite(
            '../doc/hwdb-device-tables.txt',
            setUp=hwdbDeviceTablesSetup, tearDown=tearDown,
            layer=LaunchpadZopelessLayer,
            ),
    'standing.txt': LayeredDocFileSuite(
            '../doc/standing.txt',
            layer=LaunchpadZopelessLayer,
            setUp=setUp, tearDown=tearDown,
            ),
<<<<<<< TREE
    # This test is actually run twice to prove that the AppServerLayer
    # properly isolates the database between tests.
    'launchpadlib.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,
        ),
    'launchpadlib2.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,
        ),
=======
    'google-service-stub.txt': LayeredDocFileSuite(
            '../doc/google-service-stub.txt',
            layer=GoogleServiceLayer,
            ),
>>>>>>> MERGE-SOURCE
    }


class ProcessMailLayer(LaunchpadZopelessLayer):
    """Layer containing the tests running inside process-mail.py."""


    @classmethod
    def testSetUp(cls):
        """Fixture replicating the process-mail.py environment.

        This zopeless script uses the regular security policy and
        connects as a specific DB user.
        """
        cls._old_policy = setSecurityPolicy(LaunchpadSecurityPolicy)
        LaunchpadZopelessLayer.switchDbUser(config.processmail.dbuser)

    @classmethod
    def testTearDown(cls):
        """Tear down the test fixture."""
        setSecurityPolicy(cls._old_policy)

    doctests_without_logging = [
        'answer-tracker-emailinterface.txt',
        'bugs-emailinterface.txt',
        'bugs-email-affects-path.txt',
        'emailauthentication.txt',
        ]

    doctests_with_logging = [
        'incomingmail.txt',
        'spec-mail-exploder.txt'
        ]

    @classmethod
    def addTestsToSpecial(cls):
        """Adds all the tests related to process-mail.py to special"""
        for filename in cls.doctests_without_logging:
            special[filename] = cls.createLayeredDocFileSuite(filename)

        for filename in cls.doctests_with_logging:
            special[filename] = cls.createLayeredDocFileSuite(
                filename, stdout_logging=True)

        # Adds a copy of some bug doctests that will be run with
        # the processmail user.
        def bugSetStatusSetUp(test):
            setUp(test)
            test.globs['test_dbuser'] = config.processmail.dbuser

        special['bug-set-status.txt-processmail'] = LayeredDocFileSuite(
                '../doc/bug-set-status.txt',
                setUp=bugSetStatusSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

        def bugmessageSetUp(test):
            setUp(test)
            login('no-priv@canonical.com')

        special['bugmessage.txt-processmail'] = LayeredDocFileSuite(
                '../doc/bugmessage.txt',
                setUp=bugmessageSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

    @classmethod
    def createLayeredDocFileSuite(cls, filename, stdout_logging=False):
        """Helper to create a doctest using this layer."""
        return LayeredDocFileSuite(
            "../doc/%s" % filename,
            setUp=setUp, tearDown=tearDown,
            layer=cls,
            stdout_logging=stdout_logging,
            stdout_logging_level=logging.WARNING)


ProcessMailLayer.addTestsToSpecial()


def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    for key in sorted(special):
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
        one_test = LayeredDocFileSuite(
            path, setUp=setUp, tearDown=tearDown,
            layer=LaunchpadFunctionalLayer,
            stdout_logging_level=logging.WARNING
            )
        suite.addTest(one_test)

    return suite


if __name__ == '__main__':
    unittest.main(test_suite())
