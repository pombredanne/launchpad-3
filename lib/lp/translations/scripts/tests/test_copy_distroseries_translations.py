# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test distroseries translations copying."""

__metaclass__ = type


import logging

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.testing import TestCaseWithFactory
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import LaunchpadZopelessLayer
from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.scripts.copy_distroseries_translations import (
    copy_distroseries_translations,
    )


class TestCopying(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer
    txn = FakeTransaction()

    def test_flagsHandling(self):
        """Flags are correctly restored, no matter what their values."""
        sid = getUtility(IDistributionSet)['debian']['sid']
        source = sid.previous_series

        sid.hide_all_translations = True
        sid.defer_translation_imports = True
        copy_distroseries_translations(source, sid, self.txn, logging)
        self.assertTrue(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = True
        sid.defer_translation_imports = False
        copy_distroseries_translations(source, sid, self.txn, logging)
        self.assertTrue(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = True
        copy_distroseries_translations(source, sid, self.txn, logging)
        self.assertFalse(sid.hide_all_translations)
        self.assertTrue(sid.defer_translation_imports)

        sid.hide_all_translations = False
        sid.defer_translation_imports = False
        copy_distroseries_translations(source, sid, self.txn, logging)
        self.assertFalse(sid.hide_all_translations)
        self.assertFalse(sid.defer_translation_imports)

    def test_published_packages_only(self):
        # copy_distroseries_translations's published_sources_only flag
        # restricts the copied templates to those with a corresponding
        # published source package in the target.
        distro = self.factory.makeDistribution(name='notbuntu')
        dapper = self.factory.makeDistroSeries(
            distribution=distro, name='dapper')
        spns = [self.factory.makeSourcePackageName() for i in range(3)]
        for spn in spns:
            self.factory.makePOTemplate(
                distroseries=dapper, sourcepackagename=spn)

        def get_template_spns(series):
            return [
                pot.sourcepackagename for pot in
                getUtility(IPOTemplateSet).getSubset(distroseries=series)]

        # Create a fresh series with two sources published.
        edgy = self.factory.makeDistroSeries(
            distribution=distro, name='edgy')
        self.factory.makeSourcePackagePublishingHistory(
            archive=edgy.main_archive, distroseries=edgy,
            sourcepackagename=spns[0],
            status=PackagePublishingStatus.PUBLISHED)
        self.factory.makeSourcePackagePublishingHistory(
            archive=edgy.main_archive, distroseries=edgy,
            sourcepackagename=spns[2], status=PackagePublishingStatus.PENDING)

        self.assertContentEqual(spns, get_template_spns(dapper))
        self.assertContentEqual([], get_template_spns(edgy))
        copy_distroseries_translations(
            dapper, edgy, self.txn, logging, published_sources_only=True)
        self.assertContentEqual([spns[0], spns[2]], get_template_spns(edgy))

    def test_published_packages_only_different_archive(self):
        # If an archive parameter is passed,
        # copy_distroseries_translations's published_sources_only flag
        # checks source package publications in that archive rather than in
        # the target's main archive.
        distro = self.factory.makeDistribution(name='notbuntu')
        dapper = self.factory.makeDistroSeries(
            distribution=distro, name='dapper')
        spns = [self.factory.makeSourcePackageName() for i in range(3)]
        for spn in spns:
            self.factory.makePOTemplate(
                distroseries=dapper, sourcepackagename=spn)
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)

        def get_template_spns(series):
            return [
                pot.sourcepackagename for pot in
                getUtility(IPOTemplateSet).getSubset(distroseries=series)]

        edgy = self.factory.makeDistroSeries(
            distribution=distro, name='edgy')
        edgy_derived = self.factory.makeDistroSeries(
            distribution=ppa.distribution, name='edgy-derived')
        self.factory.makeSourcePackagePublishingHistory(
            archive=ppa, distroseries=edgy_derived, sourcepackagename=spns[0],
            status=PackagePublishingStatus.PUBLISHED)
        self.factory.makeSourcePackagePublishingHistory(
            archive=edgy.main_archive, distroseries=edgy,
            sourcepackagename=spns[1],
            status=PackagePublishingStatus.PUBLISHED)
        self.factory.makeSourcePackagePublishingHistory(
            archive=ppa, distroseries=edgy_derived, sourcepackagename=spns[2],
            status=PackagePublishingStatus.PENDING)

        self.assertContentEqual(spns, get_template_spns(dapper))
        self.assertContentEqual([], get_template_spns(edgy))
        copy_distroseries_translations(
            dapper, edgy, self.txn, logging, published_sources_only=True,
            check_archive=ppa, check_distroseries=edgy_derived)
        self.assertContentEqual([spns[0], spns[2]], get_template_spns(edgy))
