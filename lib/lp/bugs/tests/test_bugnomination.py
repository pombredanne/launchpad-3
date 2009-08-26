# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug nominations."""

__metaclass__ = type

import unittest

from canonical.launchpad.ftests import login, logout
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestBugCanBeNominatedFor(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugCanBeNominatedFor, self).setUp()
        login('foo.bar@canonical.com')
        self.eric = self.factory.makePerson(name='eric')
        self.michael = self.factory.makePerson(name='michael')

        self.series = self.factory.makeProductSeries()
        self.bug = self.factory.makeBug(product=self.series.product)

    def test_canBeNominatedFor_series(self):
        # A bug may be nominated for a series of a product with an existing
        # task.
        self.assertTrue(self.bug.canBeNominatedFor(self.series))

    def test_not_canBeNominatedFor_already_nominated_series(self):
        # A bug may not be nominated for a series with an existing nomination.
        self.assertTrue(self.bug.canBeNominatedFor(self.series))
        self.bug.addNomination(self.eric, self.series)
        self.assertFalse(self.bug.canBeNominatedFor(self.series))

    def test_not_canBeNominatedFor_non_series(self):
        # A bug may not be nominated for something other than a series.
        milestone = self.factory.makeMilestone(productseries=self.series)
        self.assertFalse(self.bug.canBeNominatedFor(milestone))

    def test_not_canBeNominatedFor_already_targeted_series(self):
        # A bug may not be nominated for a series if a task already exists.
        # This case should be caught by the check for an existing nomination,
        # but there are some historical cases where a series task exists
        # without a nomination.
        self.assertTrue(self.bug.canBeNominatedFor(self.series))
        self.bug.addTask(self.eric, self.series)
        self.assertFalse(self.bug.canBeNominatedFor(self.series))

    def test_not_canBeNominatedFor_random_series(self):
        # A bug may only be nominated for a series if that series' pillar
        # already has a task.
        random_series = self.factory.makeProductSeries()
        self.assertFalse(self.bug.canBeNominatedFor(random_series))

    def tearDown(self):
        logout()
        super(TestBugCanBeNominatedFor, self).tearDown()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
