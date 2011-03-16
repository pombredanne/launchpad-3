# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test distributionsourcepackage views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.testing import (
    celebrity_logged_in,
    test_tales,
    TestCaseWithFactory,
    )
from lp.testing.matchers import BrowsesWithQueryLimit


class TestDistributionSourcePackageFormatterAPI(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_link(self):
        sourcepackagename = self.factory.makeSourcePackageName('mouse')
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        dsp = ubuntu.getSourcePackage('mouse')
        markup = (
            u'<a href="/ubuntu/+source/mouse" class="sprite package-source">'
            u'mouse in ubuntu</a>')
        self.assertEqual(markup, test_tales('dsp/fmt:link', dsp=dsp))


class TestDistributionSourcePackageChangelogView(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def test_packagediff_query_count(self):
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        spph = self.factory.makeSourcePackagePublishingHistory(
            archive=archive)
        dsp = archive.distribution.getSourcePackage(
            spph.sourcepackagerelease.sourcepackagename)
        changelog_browses_under_limit = BrowsesWithQueryLimit(
            29, self.factory.makePerson(), '+changelog')
        self.assertThat(dsp, changelog_browses_under_limit)
        with celebrity_logged_in('admin'):
            for i in range(5):
                self.factory.makePackageDiff(
                    to_source=spph.sourcepackagerelease)
        self.assertThat(dsp, changelog_browses_under_limit)
