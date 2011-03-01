# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

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
from zope.testing.cleanup import cleanUp

from canonical.config import config
from canonical.database.sqlbase import commit
from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    )
from canonical.launchpad.testing import browser
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite,
    setGlobs,
    setUp,
    tearDown,
    )
from canonical.launchpad.webapp.authorization import LaunchpadSecurityPolicy
from canonical.launchpad.webapp.tests import test_notifications
from canonical.testing.layers import (
    AppServerLayer,
    BaseLayer,
    FunctionalLayer,
    GoogleLaunchpadFunctionalLayer,
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.bugs.interfaces.bug import CreateBugParams
from lp.bugs.interfaces.bugtask import IBugTaskSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.services.worlddata.interfaces.language import ILanguageSet
from lp.testing.mail_helpers import pop_notifications


here = os.path.dirname(os.path.realpath(__file__))


def lobotomize_stevea():
    """Set SteveA's email address' status to NEW.

    Call this method first in a test's setUp where needed. Tests
    using this function should be refactored to use the unaltered
    sample data and this function eventually removed.

    In the past, SteveA's account erroneously appeared in the old
    ValidPersonOrTeamCache materialized view. This materialized view
    has since been replaced and now SteveA is correctly listed as
    invalid in the sampledata. This fix broke some tests testing
    code that did not use the ValidPersonOrTeamCache to determine
    validity.
    """
    from canonical.launchpad.database.emailaddress import EmailAddress
    from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
    stevea_emailaddress = EmailAddress.byEmail(
            'steve.alexander@ubuntulinux.com')
    stevea_emailaddress.status = EmailAddressStatus.NEW
    commit()


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


def archivepublisherSetUp(test):
    """Setup the archive publisher script tests."""
    setUp(test)
    LaunchpadZopelessLayer.switchDbUser(config.archivepublisher.dbuser)


def branchscannerSetUp(test):
    """Setup the user for the branch scanner tests."""
    LaunchpadZopelessLayer.switchDbUser(config.branchscanner.dbuser)
    setUp(test)


def branchscannerTearDown(test):
    """Tear down the branch scanner tests."""
    # XXX sinzui 2007-11-14:
    # This function is not needed. The test should be switched to tearDown.
    tearDown(test)


def uploadQueueSetUp(test):
    lobotomize_stevea()
    test_dbuser = config.uploadqueue.dbuser
    LaunchpadZopelessLayer.switchDbUser(test_dbuser)
    setUp(test)
    test.globs['test_dbuser'] = test_dbuser


def layerlessTearDown(test):
    """Clean up any Zope registrations."""
    cleanUp()


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
    # Remove the notifications for the newly created question.
    pop_notifications()
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


# Files that have special needs can construct their own suite
special = {
    # No setup or teardown at all, since it is demonstrating these features.
    'old-testing.txt': LayeredDocFileSuite(
        '../doc/old-testing.txt', layer=FunctionalLayer),

    # And this test want minimal environment too.
    'package-relationship.txt': LayeredDocFileSuite(
        '../doc/package-relationship.txt',
        stdout_logging=False, layer=None),

    'webservice-configuration.txt': LayeredDocFileSuite(
        '../doc/webservice-configuration.txt',
        setUp=setGlobs, tearDown=layerlessTearDown, layer=None),


    # POExport stuff is Zopeless and connects as a different database user.
    # poexport-distroseries-(date-)tarball.txt is excluded, since they add
    # data to the database as well.
    'message.txt': LayeredDocFileSuite(
        '../doc/message.txt',
        setUp=setUp, tearDown=tearDown, layer=LaunchpadFunctionalLayer),
    'close-account.txt': LayeredDocFileSuite(
        '../doc/close-account.txt', setUp=setUp, tearDown=tearDown,
        layer=LaunchpadZopelessLayer),
    'launchpadform.txt': LayeredDocFileSuite(
        '../doc/launchpadform.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer),
    'launchpadformharness.txt': LayeredDocFileSuite(
        '../doc/launchpadformharness.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer),
    'uri.txt': LayeredDocFileSuite(
        '../doc/uri.txt',
        setUp=setUp, tearDown=tearDown,
        layer=FunctionalLayer),
    'notification-text-escape.txt': LayeredDocFileSuite(
        '../doc/notification-text-escape.txt',
        setUp=test_notifications.setUp,
        tearDown=test_notifications.tearDown,
        stdout_logging=False, layer=None),
    # This test is actually run twice to prove that the AppServerLayer
    # properly isolates the database between tests.
    'launchpadlib.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,),
    'launchpadlib2.txt': LayeredDocFileSuite(
        '../doc/launchpadlib.txt',
        layer=AppServerLayer,
        setUp=browser.setUp, tearDown=browser.tearDown,),
    # XXX gary 2008-12-08 bug=306246 bug=305858: Disabled test because of
    # multiple spurious problems with layer and test.
    # 'google-service-stub.txt': LayeredDocFileSuite(
    #     '../doc/google-service-stub.txt',
    #     layer=GoogleServiceLayer,),
    'canonical_url.txt': LayeredDocFileSuite(
        '../doc/canonical_url.txt',
        setUp=setUp,
        tearDown=tearDown,
        layer=FunctionalLayer,),
    'google-searchservice.txt': LayeredDocFileSuite(
        '../doc/google-searchservice.txt',
        setUp=setUp, tearDown=tearDown,
        layer=GoogleLaunchpadFunctionalLayer,),
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

    doctests = [
        '../../../lp/answers/tests/emailinterface.txt',
        '../../../lp/bugs/tests/bugs-emailinterface.txt',
        '../../../lp/bugs/doc/bugs-email-affects-path.txt',
        '../doc/emailauthentication.txt',
        ]

    @classmethod
    def addTestsToSpecial(cls):
        """Adds all the tests related to process-mail.py to special"""
        for filepath in cls.doctests:
            filename = os.path.basename(filepath)
            special[filename] = LayeredDocFileSuite(
                filepath,
                setUp=setUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

        # Adds a copy of some bug doctests that will be run with
        # the processmail user.
        def bugSetStatusSetUp(test):
            setUp(test)
            test.globs['test_dbuser'] = config.processmail.dbuser

        special['bug-set-status.txt-processmail'] = LayeredDocFileSuite(
                '../../../lp/bugs/doc/bug-set-status.txt',
                setUp=bugSetStatusSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)

        def bugmessageSetUp(test):
            setUp(test)
            login('no-priv@canonical.com')

        special['bugmessage.txt-processmail'] = LayeredDocFileSuite(
                '../../../lp/bugs/doc/bugmessage.txt',
                setUp=bugmessageSetUp, tearDown=tearDown,
                layer=cls,
                stdout_logging=False)


ProcessMailLayer.addTestsToSpecial()


def test_suite():
    suite = unittest.TestSuite()

    # Add special needs tests
    for key in sorted(special):
        special_suite = special[key]
        suite.addTest(special_suite)

    testsdir = os.path.abspath(
        os.path.normpath(os.path.join(here, '..', 'doc')))

    # Add tests using default setup/teardown
    filenames = [filename
                 for filename in os.listdir(testsdir)
                 if filename.lower().endswith('.txt')
                    and filename not in special]
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
            stdout_logging_level=logging.WARNING)
        suite.addTest(one_test)

    return suite


if __name__ == '__main__':
    unittest.main(test_suite())
