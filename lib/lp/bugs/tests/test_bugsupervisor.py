# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Run tests against IHasBugSupervisor implementations."""

from zope.security.interfaces import ForbiddenAttribute

from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class BugSupervisorMixin:

    def test_cannot_be_set_directly(self):
        # The bug_supervisor attribute can not be directly set.
        self.assertRaises(
            ForbiddenAttribute, setattr, self.target, 'bug_supervisor', None)

    def test_set_bug_supervisor(self):
        # The bug_supervisor attribute can be set by calling .setBugSupervisor.
        person = self.factory.makePerson()
        with person_logged_in(self.target.owner):
            self.target.setBugSupervisor(person, None)
        self.assertEqual(person, self.target.bug_supervisor)


class TestProductBugSupervisor(TestCaseWithFactory, BugSupervisorMixin):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductBugSupervisor, self).setUp()
        self.target = self.factory.makeProduct()


class TestDistributionBugSupervisor(TestCaseWithFactory, BugSupervisorMixin):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionBugSupervisor, self).setUp()
        self.target = self.factory.makeDistribution()
