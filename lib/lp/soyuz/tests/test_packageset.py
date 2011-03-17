# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Packageset features."""

from zope.component import getUtility

from canonical.testing.layers import LaunchpadZopelessLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.interfaces.packageset import (
    DuplicatePackagesetName,
    IPackagesetSet,
    )
from lp.testing import TestCaseWithFactory


class TestPackagesetSet(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup a distribution with multiple distroseries."""
        super(TestPackagesetSet, self).setUp()
        self.distribution = getUtility(IDistributionSet).getByName(
            'ubuntu')
        self.distroseries_current = self.distribution.currentseries
        self.distroseries_experimental = self.factory.makeDistroRelease(
            distribution = self.distribution, name="experimental",
            status=SeriesStatus.EXPERIMENTAL)

        self.person1 = self.factory.makePerson(
            name='hacker', displayname=u'Happy Hacker')

        self.packageset_set = getUtility(IPackagesetSet)

    def test_new_defaults_to_current_distroseries(self):
        # If the distroseries is not provided, the current development
        # distroseries will be assumed.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)

        self.failUnlessEqual(
            self.distroseries_current, packageset.distroseries)

    def test_new_with_specified_distroseries(self):
        # A distroseries can be provided when creating a package set.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1,
            distroseries=self.distroseries_experimental)

        self.failUnlessEqual(
            self.distroseries_experimental, packageset.distroseries)

    def test_new_creates_new_packageset_group(self):
        # Creating a new packageset should also create a new packageset
        # group with the same owner.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1,
            distroseries=self.distroseries_experimental)

        self.failUnlessEqual(
            self.person1, packageset.packagesetgroup.owner)

    def test_new_duplicate_name_for_same_distroseries(self):
        # Creating a packageset with a duplicate name for the
        # given distroseries will fail.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1,
            distroseries=self.distroseries_experimental)

        self.failUnlessRaises(
            DuplicatePackagesetName, self.packageset_set.new,
            u'kernel', u'A packageset with a duplicate name', self.person1,
            distroseries=self.distroseries_experimental)

    def test_new_duplicate_name_for_different_distroseries(self):
        # Creating a packageset with a duplicate name but for a different
        # series is no problem.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)

        packageset2 = self.packageset_set.new(
            u'kernel', u'A packageset with a duplicate name', self.person1,
            distroseries=self.distroseries_experimental)
        self.assertEqual(packageset.name, packageset2.name)

    def test_new_related_packageset(self):
        # Creating a new package set while specifying a `related_set` should
        # have the effect that the former ends up in the same group as the
        # latter.
        pset1 = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)

        pset2 = self.packageset_set.new(
            u'kernel', u'A related package set.', self.person1,
            distroseries=self.distroseries_experimental, related_set=pset1)
        self.assertEqual(pset1.packagesetgroup, pset2.packagesetgroup)

    def test_get_by_name_in_current_distroseries(self):
        # IPackagesetSet.getByName() will return the package set in the
        # current distroseries if the optional `distroseries` parameter is
        # omitted.
        pset1 = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)
        pset2 = self.packageset_set.new(
            u'kernel', u'A related package set.', self.person1,
            distroseries=self.distroseries_experimental, related_set=pset1)
        pset_found = getUtility(IPackagesetSet).getByName('kernel')
        self.assertEqual(pset1, pset_found)

    def test_get_by_name_in_specified_distroseries(self):
        # IPackagesetSet.getByName() will return the package set in the
        # specified distroseries.
        pset1 = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)
        pset2 = self.packageset_set.new(
            u'kernel', u'A related package set.', self.person1,
            distroseries=self.distroseries_experimental, related_set=pset1)
        pset_found = getUtility(IPackagesetSet).getByName(
            'kernel', distroseries=self.distroseries_experimental)
        self.assertEqual(pset2, pset_found)


class TestPackageset(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Setup a distribution with multiple distroseries."""
        super(TestPackageset, self).setUp()
        self.distribution = getUtility(IDistributionSet).getByName(
            'ubuntu')
        self.distroseries_current = self.distribution.currentseries
        self.distroseries_experimental = self.factory.makeDistroRelease(
            distribution = self.distribution, name="experimental",
            status=SeriesStatus.EXPERIMENTAL)
        self.distroseries_experimental2 = self.factory.makeDistroRelease(
            distribution = self.distribution, name="experimental2",
            status=SeriesStatus.EXPERIMENTAL)

        self.person1 = self.factory.makePerson(
            name='hacker', displayname=u'Happy Hacker')

        self.packageset_set = getUtility(IPackagesetSet)

    def test_no_related_sets(self):
        # If the package set is the only one in the group the result set
        # returned by relatedSets() is empty.
        packageset = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)

        self.failUnlessEqual(packageset.relatedSets().count(), 0)

    def test_related_set_found(self):
        # Creating a new package set while specifying a `related_set` should
        # have the effect that the former ends up in the same group as the
        # latter.

        # The original package set.
        pset1 = self.packageset_set.new(
            u'kernel', u'Contains all OS kernel packages', self.person1)

        # A related package set.
        pset2 = self.packageset_set.new(
            u'kernel', u'A related package set.', self.person1,
            distroseries=self.distroseries_experimental, related_set=pset1)
        self.assertEqual(pset1.packagesetgroup, pset2.packagesetgroup)

        # An unrelated package set with the same name.
        pset3 = self.packageset_set.new(
            u'kernel', u'Unrelated package set.', self.person1,
            distroseries=self.distroseries_experimental2)
        self.assertNotEqual(pset2.packagesetgroup, pset3.packagesetgroup)

        # Make sure 'pset2' is related to 'pset1'.
        related = pset1.relatedSets()
        self.assertEqual(related.count(), 1)
        self.assertEqual(related[0], pset2)

        # And the other way around ..
        related = pset2.relatedSets()
        self.assertEqual(related.count(), 1)
        self.assertEqual(related[0], pset1)

        # Unsurprisingly, the unrelated package set is not associated with any
        # other package set.
        self.failUnlessEqual(pset3.relatedSets().count(), 0)
