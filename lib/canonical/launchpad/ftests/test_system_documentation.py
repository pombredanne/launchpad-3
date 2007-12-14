# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
"""
Test the examples included in the system documentation in
lib/canonical/launchpad/doc.
"""
# pylint: disable-msg=C0103

import logging
import os
import transaction
import unittest

from zope.component import getUtility, getView
from zope.security.management import setSecurityPolicy
from zope.testing.doctest import REPORT_NDIFF, NORMALIZE_WHITESPACE, ELLIPSIS
from zope.testing.doctest import DocFileSuite

from canonical.authserver.tests.harness import AuthserverTacTestSetup
from canonical.config import config
from canonical.database.sqlbase import (
    commit, flush_database_updates, READ_COMMITTED_ISOLATION)
from canonical.functional import FunctionalDocFileSuite, StdoutHandler
from canonical.launchpad.ftests import ANONYMOUS, login, logout
from canonical.launchpad.ftests import mailinglists_helper
from canonical.launchpad.ftests.bug import (
    create_old_bug, summarize_bugtasks, sync_bugtasks)
from canonical.launchpad.interfaces import (
    CreateBugParams, IBugTaskSet, IDistributionSet, ILanguageSet, ILaunchBag,
    IPersonSet)
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.tests.mail_helpers import pop_notifications
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing import (
    LaunchpadZopelessLayer, LaunchpadFunctionalLayer,DatabaseLayer,
    FunctionalLayer)


here = os.path.dirname(os.path.realpath(__file__))

default_optionflags = REPORT_NDIFF | NORMALIZE_WHITESPACE | ELLIPSIS


def create_view(context, name, form=None, layer=None, server_url=None,
                method='GET'):
    """Return a view based on the given arguments.

    :param context: The context for the view.
    :param name: The web page the view should handle.
    :param form: A dictionary with the form keys.
    :param layer: The layer where the page we are interested in is located.
    :param server_url: The URL from where this request was done.
    :param method: The method used in the request. Defaults to 'GET'.
    :return: The view class for the given context and the name.
    """
    request = LaunchpadTestRequest(
        form=form, SERVER_URL=server_url, method=method)
    if layer is not None:
        setFirstLayer(request, layer)
    return getView(context, name, request)


def setGlobs(test):
    """Add the common globals for testing system documentation."""
    test.globs['ANONYMOUS'] = ANONYMOUS
    test.globs['login'] = login
    test.globs['logout'] = logout
    test.globs['ILaunchBag'] = ILaunchBag
    test.globs['getUtility'] = getUtility
    test.globs['transaction'] = transaction
    test.globs['flush_database_updates'] = flush_database_updates
    test.globs['create_view'] = create_view


def setUp(test):
    """Setup the common globals and login for testing system documentation."""
    setGlobs(test)
    # Set up an anonymous interaction.
    login(ANONYMOUS)


def tearDown(test):
    """Tear down the common system documentation test."""
    logout()

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
    LaunchpadZopelessLayer.alterConnection(
        dbuser=config.builddmaster.dbuser,
        isolation=READ_COMMITTED_ISOLATION)
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


def LayeredDocFileSuite(*args, **kw):
    '''Create a DocFileSuite with a layer.'''
    # Set stdout_logging keyword argument to True to make
    # logging output be sent to stdout, forcing doctests to deal with it.
    stdout_logging = kw.pop('stdout_logging', True)
    stdout_logging_level = kw.pop('stdout_logging_level', logging.INFO)

    kw_setUp = kw.get('setUp')
    def setUp(test):
        if kw_setUp is not None:
            kw_setUp(test)
        if stdout_logging:
            log = StdoutHandler('')
            log.setLoggerLevel(stdout_logging_level)
            log.install()
            test.globs['log'] = log
            # Store as instance attribute so we can uninstall it.
            test._stdout_logger = log
    kw['setUp'] = setUp

    kw_tearDown = kw.get('tearDown')
    def tearDown(test):
        if kw_tearDown is not None:
            kw_tearDown(test)
        if stdout_logging:
            test._stdout_logger.uninstall()
    kw['tearDown'] = tearDown

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

    # And this test want minimal environment too.
    'package-relationship.txt': DocFileSuite(
            '../doc/package-relationship.txt',
            optionflags=default_optionflags
            ),

    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distroseries-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
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
    'nascentupload.txt': LayeredDocFileSuite(
            '../doc/nascentupload.txt',
            setUp=uploaderSetUp, tearDown=uploaderTearDown,
            layer=LaunchpadZopelessLayer, optionflags=default_optionflags
            ),
    'build-notification.txt': LayeredDocFileSuite(
            '../doc/build-notification.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer, optionflags=default_optionflags
            ),
    'buildd-slavescanner.txt': LayeredDocFileSuite(
            '../doc/buildd-slavescanner.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer, optionflags=default_optionflags,
            stdout_logging_level=logging.WARNING
            ),
    'buildd-scoring.txt': LayeredDocFileSuite(
            '../doc/buildd-scoring.txt',
            setUp=builddmasterSetUp,
            layer=LaunchpadZopelessLayer, optionflags=default_optionflags,
            stdout_logging_level=logging.DEBUG
            ),
    'revision.txt': LayeredDocFileSuite(
            '../doc/revision.txt',
            setUp=branchscannerSetUp, tearDown=branchscannerTearDown,
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
            layer=LaunchpadZopelessLayer, setUp=bugNotificationSendingSetUp,
            tearDown=bugNotificationSendingTearDown
            ),
    'bugmail-headers.txt': LayeredDocFileSuite(
            '../doc/bugmail-headers.txt',
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer,
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
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'script-monitoring.txt': LayeredDocFileSuite(
            '../doc/script-monitoring.txt',
            setUp=setUp, tearDown=tearDown, optionflags=default_optionflags,
            layer=LaunchpadZopelessLayer
            ),
    'distroseriesqueue-debian-installer.txt': FunctionalDocFileSuite(
            '../doc/distroseriesqueue-debian-installer.txt',
            setUp=distroseriesqueueSetUp, tearDown=distroseriesqueueTearDown,
            optionflags=default_optionflags,
            layer=LaunchpadFunctionalLayer
            ),
    'bug-set-status.txt': LayeredDocFileSuite(
            '../doc/bug-set-status.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'closing-bugs-from-changelogs.txt': LayeredDocFileSuite(
            '../doc/closing-bugs-from-changelogs.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'bugtask-expiration.txt': LayeredDocFileSuite(
            '../doc/bugtask-expiration.txt',
            setUp=bugtaskExpirationSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'bugmessage.txt': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=noPrivSetUp, tearDown=tearDown,
            optionflags=default_optionflags, layer=LaunchpadFunctionalLayer
            ),
    'bugmessage.txt-queued': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=uploadQueueSetUp,
            tearDown=uploadQueueTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'bugmessage.txt-uploader': LayeredDocFileSuite(
            '../doc/bugmessage.txt',
            setUp=uploaderSetUp,
            tearDown=uploaderTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'bug-private-by-default.txt': LayeredDocFileSuite(
            '../doc/bug-private-by-default.txt',
            setUp=setUp,
            tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadZopelessLayer
            ),
    'answer-tracker-notifications-linked-bug.txt': LayeredDocFileSuite(
            '../doc/answer-tracker-notifications-linked-bug.txt',
            setUp=bugLinkedToQuestionSetUp, tearDown=tearDown,
            optionflags=default_optionflags, layer=LaunchpadFunctionalLayer
            ),
    'answer-tracker-notifications-linked-bug.txt-uploader':
            LayeredDocFileSuite(
                '../doc/answer-tracker-notifications-linked-bug.txt',
                setUp=uploaderBugLinkedToQuestionSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'answer-tracker-notifications-linked-bug.txt-queued': LayeredDocFileSuite(
            '../doc/answer-tracker-notifications-linked-bug.txt',
            setUp=uploadQueueBugLinkedToQuestionSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer
            ),
    'mailinglist-xmlrpc.txt': FunctionalDocFileSuite(
            '../doc/mailinglist-xmlrpc.txt',
            setUp=mailingListXMLRPCInternalSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadFunctionalLayer
            ),
    'mailinglist-xmlrpc.txt-external': FunctionalDocFileSuite(
            '../doc/mailinglist-xmlrpc.txt',
            setUp=mailingListXMLRPCExternalSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadFunctionalLayer,
            ),
    'externalbugtracker-bugzilla.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-bugzilla.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-bugzilla-oddities.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-bugzilla-oddities.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-checkwatches.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-checkwatches.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-debbugs.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-debbugs.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-mantis-csv.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-mantis-csv.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-mantis.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-mantis.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-python.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-python.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-roundup.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-roundup.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-sourceforge.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-sourceforge.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'externalbugtracker-trac.txt':
            LayeredDocFileSuite(
                '../doc/externalbugtracker-trac.txt',
                setUp=checkwatchesSetUp,
                tearDown=tearDown,
                optionflags=default_optionflags, layer=LaunchpadZopelessLayer
                ),
    'mailinglist-subscriptions-xmlrpc.txt': FunctionalDocFileSuite(
            '../doc/mailinglist-subscriptions-xmlrpc.txt',
            setUp=mailingListXMLRPCInternalSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadFunctionalLayer
            ),
    'mailinglist-subscriptions-xmlrpc.txt-external': FunctionalDocFileSuite(
            '../doc/mailinglist-subscriptions-xmlrpc.txt',
            setUp=mailingListXMLRPCExternalSetUp,
            tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadFunctionalLayer,
            ),
    'codeimport-machine.txt': LayeredDocFileSuite(
            '../doc/codeimport-machine.txt',
            setUp=zopelessLaunchpadSecuritySetUp,
            tearDown=zopelessLaunchpadSecurityTearDown,
            optionflags=default_optionflags, layer=LaunchpadZopelessLayer,
            ),
    # Also run the pillar.txt doctest under the Zopeless layer.
    # This exposed bug #149632.
    'pillar.txt-zopeless': LayeredDocFileSuite(
            '../doc/pillar.txt',
            setUp=setUp, tearDown=tearDown,
            optionflags=default_optionflags,
            layer=LaunchpadZopelessLayer
            ),
    'openid-fetcher.txt': FunctionalDocFileSuite(
            '../doc/openid-fetcher.txt',
            optionflags=default_optionflags,
            stdout_logging=False,
            layer=LaunchpadFunctionalLayer
            ),
    'soyuz-set-of-uploads.txt': LayeredDocFileSuite(
            '../doc/soyuz-set-of-uploads.txt',
            layer=LaunchpadZopelessLayer, optionflags=default_optionflags
            ),
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
                optionflags=default_optionflags, layer=cls,
                stdout_logging=False)

        def bugmessageSetUp(test):
            setUp(test)
            login('no-priv@canonical.com')

        special['bugmessage.txt-processmail'] = LayeredDocFileSuite(
                '../doc/bugmessage.txt',
                setUp=bugmessageSetUp, tearDown=tearDown,
                optionflags=default_optionflags, layer=cls,
                stdout_logging=False)

    @classmethod
    def createLayeredDocFileSuite(cls, filename, stdout_logging=False):
        """Helper to create a doctest using this layer."""
        return LayeredDocFileSuite(
            "../doc/%s" % filename,
            setUp=setUp, tearDown=tearDown,
            optionflags=default_optionflags, layer=cls,
            stdout_logging=stdout_logging,
            stdout_logging_level=logging.WARNING)


ProcessMailLayer.addTestsToSpecial()


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
