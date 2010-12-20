# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for bug nomiation views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.webapp.interfaces import ILaunchBag
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestBugNominationView(TestCaseWithFactory):
    """Tests for BugNominationView."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugNominationView, self).setUp()
        self.distribution = self.factory.makeDistribution()
        owner = self.distribution.owner
        bug_team = self.factory.makeTeam(owner=owner)
        self.bug_worker = self.factory.makePerson()
        with person_logged_in(owner):
            bug_team.addMember(self.bug_worker, owner)
            self.distribution.setBugSupervisor(bug_team, owner)
            self.distribution.driver = self.factory.makePerson()
        self.bug_task = self.factory.makeBugTask(target=self.distribution)
        launchbag = getUtility(ILaunchBag)
        launchbag.add(self.distribution)
        launchbag.add(self.bug_task)

    def test_submit_action_bug_supervisor(self):
        # A bug supervisor sees the Nominate action label.
        login_person(self.bug_worker)
        view = create_initialized_view(self.bug_task, name='+nominate')
        action = view.__class__.actions.byname['actions.submit']
        self.assertEqual('Nominate', action.label)

    def test_submit_action_driver(self):
        # A driver sees the Target action label.
        login_person(self.distribution.driver)
        view = create_initialized_view(self.bug_task, name='+nominate')
        action = view.__class__.actions.byname['actions.submit']
        self.assertEqual('Target', action.label)
