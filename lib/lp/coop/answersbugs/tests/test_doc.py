# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import logging
import os
import unittest

from zope.component import getUtility

from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.ftests.test_system_documentation import (
    uploaderSetUp, uploadQueueSetUp)
from canonical.launchpad.interfaces import (
    CreateBugParams, IBugTaskSet, IDistributionSet, ILanguageSet,
    IPersonSet)
from canonical.launchpad.testing.pages import PageTestSuite
from canonical.launchpad.testing.systemdocs import (
    LayeredDocFileSuite, setUp, tearDown)
from lp.testing.mail_helpers import pop_notifications
from canonical.testing import DatabaseFunctionalLayer, LaunchpadZopelessLayer

from lp.services.testing import build_test_suite

here = os.path.dirname(os.path.realpath(__file__))


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
    'notifications-linked-private-bug.txt':
            LayeredDocFileSuite(
            'notifications-linked-private-bug.txt',
            setUp=bugLinkedToQuestionSetUp, tearDown=tearDown,
            layer=DatabaseFunctionalLayer
            ),
    'notifications-linked-bug.txt': LayeredDocFileSuite(
            'notifications-linked-bug.txt',
            setUp=bugLinkedToQuestionSetUp, tearDown=tearDown,
            layer=DatabaseFunctionalLayer
            ),
    'notifications-linked-bug.txt-uploader':
            LayeredDocFileSuite(
                'notifications-linked-bug.txt',
                setUp=uploaderBugLinkedToQuestionSetUp,
                tearDown=tearDown,
                layer=LaunchpadZopelessLayer
                ),
    'notifications-linked-bug.txt-queued': LayeredDocFileSuite(
            'notifications-linked-bug.txt',
            setUp=uploadQueueBugLinkedToQuestionSetUp,
            tearDown=tearDown,
            layer=LaunchpadZopelessLayer
            ),
    }


def test_suite():
    return build_test_suite(here, special)
