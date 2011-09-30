# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Packageset features."""

from zope.component import getUtility

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.series import SeriesStatus
from lp.soyuz.interfaces.packageset import (
    DuplicatePackagesetName,
    IPackagesetSet,
    )
from lp.testing import TestCaseWithFactory


class TestPackagesetSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def getUbuntu(self):
        """Get the Ubuntu `Distribution`."""
        return getUtility(IDistributionSet).getByName('ubuntu')

    def makeExperimentalSeries(self):
        """Create an experimental Ubuntu `DistroSeries`."""
        return self.factory.makeDistroSeries(
            distribution=self.getUbuntu(), name="experimental",
            status=SeriesStatus.EXPERIMENTAL)

    def test_new_defaults_to_current_distroseries(self):
        # If the distroseries is not provided, the current development
        # distroseries will be assumed.
        packageset = getUtility(IPackagesetSet).new(
            self.factory.getUniqueUnicode(), self.factory.getUniqueUnicode(),
            self.factory.makePerson())
        self.failUnlessEqual(
            self.getUbuntu().currentseries, packageset.distroseries)

    def test_new_with_specified_distroseries(self):
        # A distroseries can be provided when creating a package set.
        experimental_series = self.makeExperimentalSeries()
        packageset = getUtility(IPackagesetSet).new(
            self.factory.getUniqueUnicode(), self.factory.getUniqueUnicode(),
            self.factory.makePerson(), distroseries=experimental_series)
        self.failUnlessEqual(experimental_series, packageset.distroseries)

    def test_new_creates_new_packageset_group(self):
        # Creating a new packageset should also create a new packageset
        # group with the same owner.
        owner = self.factory.makePerson()
        experimental_series = self.makeExperimentalSeries()
        packageset = getUtility(IPackagesetSet).new(
            self.factory.getUniqueUnicode(), self.factory.getUniqueUnicode(),
            owner, distroseries=experimental_series)
        self.failUnlessEqual(owner, packageset.packagesetgroup.owner)

    def test_new_duplicate_name_for_same_distroseries(self):
        # Creating a packageset with a duplicate name for the
        # given distroseries will fail.
        distroseries = self.factory.makeDistroSeries()
        name = self.factory.getUniqueUnicode()
        self.factory.makePackageset(name, distroseries=distroseries)
        self.assertRaises(
            DuplicatePackagesetName, getUtility(IPackagesetSet).new,
            name, self.factory.getUniqueUnicode(), self.factory.makePerson(),
            distroseries=distroseries)

    def test_new_duplicate_name_for_different_distroseries(self):
        # Creating a packageset with a duplicate name but for a different
        # series is no problem.
        name = self.factory.getUniqueUnicode()
        packageset1 = self.factory.makePackageset(name)
        packageset2 = getUtility(IPackagesetSet).new(
            name, self.factory.getUniqueUnicode(), self.factory.makePerson(),
            distroseries=self.factory.makeDistroSeries())
        self.assertEqual(packageset1.name, packageset2.name)

    def test_new_related_packageset(self):
        # Creating a new package set while specifying a `related_set` should
        # have the effect that the former ends up in the same group as the
        # latter.
        name = self.factory.getUniqueUnicode()
        pset1 = self.factory.makePackageset(name)
        pset2 = self.factory.makePackageset(
            name, distroseries=self.makeExperimentalSeries(),
            related_set=pset1)
        self.assertEqual(pset1.packagesetgroup, pset2.packagesetgroup)

    def test_get_by_name_in_current_distroseries(self):
        # IPackagesetSet.getByName() will return the package set in the
        # current distroseries if the optional `distroseries` parameter is
        # omitted.
        name = self.factory.getUniqueUnicode()
        pset1 = self.factory.makePackageset(name)
        self.factory.makePackageset(
            name, distroseries=self.makeExperimentalSeries(),
            related_set=pset1)
        self.assertEqual(pset1, getUtility(IPackagesetSet).getByName(name))

    def test_get_by_name_in_specified_distroseries(self):
        # IPackagesetSet.getByName() will return the package set in the
        # specified distroseries.
        name = self.factory.getUniqueUnicode()
        experimental_series = self.makeExperimentalSeries()
        pset1 = self.factory.makePackageset(name)
        pset2 = self.factory.makePackageset(
            name, distroseries=experimental_series, related_set=pset1)
        pset_found = getUtility(IPackagesetSet).getByName(
            name, distroseries=experimental_series)
        self.assertEqual(pset2, pset_found)

    def test_get_by_distroseries(self):
        # IPackagesetSet.getBySeries() will return those package sets
        # associated with the given distroseries.
        package_sets_for_current_ubuntu = [
            self.factory.makePackageset() for counter in xrange(2)]
        self.factory.makePackageset(
            distroseries=self.makeExperimentalSeries())
        self.assertContentEqual(
            package_sets_for_current_ubuntu,
            getUtility(IPackagesetSet).getBySeries(
                self.getUbuntu().currentseries))

    def test_getForPackages_returns_packagesets(self):
        # getForPackages finds package sets for given source package
        # names in a distroseries, and maps them by
        # SourcePackageName.id.
        series = self.factory.makeDistroSeries()
        packageset = self.factory.makePackageset(distroseries=series)
        package = self.factory.makeSourcePackageName()
        packageset.addSources([package.name])
        self.assertEqual(
            {package.id: [packageset]},
            getUtility(IPackagesetSet).getForPackages(series, [package.id]))

    def test_getForPackages_filters_by_distroseries(self):
        # getForPackages does not return packagesets for different
        # distroseries.
        series = self.factory.makeDistroSeries()
        other_series = self.factory.makeDistroSeries()
        packageset = self.factory.makePackageset(distroseries=series)
        package = self.factory.makeSourcePackageName()
        packageset.addSources([package.name])
        self.assertEqual(
            {},
            getUtility(IPackagesetSet).getForPackages(
                other_series, [package.id]))

    def test_getForPackages_filters_by_sourcepackagename(self):
        # getForPackages does not return packagesets for different
        # source package names.
        series = self.factory.makeDistroSeries()
        packageset = self.factory.makePackageset(distroseries=series)
        package = self.factory.makeSourcePackageName()
        other_package = self.factory.makeSourcePackageName()
        packageset.addSources([package.name])
        self.assertEqual(
            {},
            getUtility(IPackagesetSet).getForPackages(
                series, [other_package.id]))


class TestPackageset(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        """Setup a distribution with multiple distroseries."""
        super(TestPackageset, self).setUp()
        self.distribution = getUtility(IDistributionSet).getByName(
            'ubuntu')
        self.distroseries_current = self.distribution.currentseries
        self.distroseries_experimental = self.factory.makeDistroSeries(
            distribution=self.distribution, name="experimental",
            status=SeriesStatus.EXPERIMENTAL)
        self.distroseries_experimental2 = self.factory.makeDistroSeries(
            distribution=self.distribution, name="experimental2",
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
