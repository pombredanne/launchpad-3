# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests related to bug nominations."""

__metaclass__ = type

from canonical.launchpad.ftests import (
    login,
    logout,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class CanBeNominatedForTestMixin:
    """Test case mixin for IBug.canBeNominatedFor."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(CanBeNominatedForTestMixin, self).setUp()
        login('foo.bar@canonical.com')
        self.eric = self.factory.makePerson(name='eric')
        self.setUpTarget()

    def tearDown(self):
        logout()
        super(CanBeNominatedForTestMixin, self).tearDown()

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
        self.assertFalse(self.bug.canBeNominatedFor(self.milestone))

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
        self.assertFalse(self.bug.canBeNominatedFor(self.random_series))


class TestBugCanBeNominatedForProductSeries(
    CanBeNominatedForTestMixin, TestCaseWithFactory):
    """Test IBug.canBeNominated for IProductSeries nominations."""

    def setUpTarget(self):
        self.series = self.factory.makeProductSeries()
        self.bug = self.factory.makeBug(product=self.series.product)
        self.milestone = self.factory.makeMilestone(productseries=self.series)
        self.random_series = self.factory.makeProductSeries()


class TestBugCanBeNominatedForDistroSeries(
    CanBeNominatedForTestMixin, TestCaseWithFactory):
    """Test IBug.canBeNominated for IDistroSeries nominations."""

    def setUpTarget(self):
        self.series = self.factory.makeDistroRelease()
        # The factory can't create a distro bug directly.
        self.bug = self.factory.makeBug()
        self.bug.addTask(self.eric, self.series.distribution)
        self.milestone = self.factory.makeMilestone(
            distribution=self.series.distribution)
        self.random_series = self.factory.makeDistroRelease()

    def test_not_canBeNominatedFor_source_package(self):
        # A bug may not be nominated directly for a source package. The
        # distroseries must be nominated instead.
        spn = self.factory.makeSourcePackageName()
        source_package = self.series.getSourcePackage(spn)
        self.assertFalse(self.bug.canBeNominatedFor(source_package))

    def test_canBeNominatedFor_with_only_distributionsourcepackage(self):
        # A distribution source package task is sufficient to allow nomination
        # to a series of that distribution.
        sp_bug = self.factory.makeBug()
        spn = self.factory.makeSourcePackageName()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=self.series, sourcepackagename=spn)

        self.assertFalse(sp_bug.canBeNominatedFor(self.series))
        sp_bug.addTask(
            self.eric, self.series.distribution.getSourcePackage(spn))
        self.assertTrue(sp_bug.canBeNominatedFor(self.series))
