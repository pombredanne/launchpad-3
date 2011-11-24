# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test distributionsourcepackage views."""

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.app.enums import ServiceUsage
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.testing import (
    celebrity_logged_in,
    test_tales,
    TestCaseWithFactory,
    )
from lp.testing.matchers import BrowsesWithQueryLimit
from lp.testing.views import create_view


class TestDistributionSourcePackageFormatterAPI(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_link(self):
        sourcepackagename = self.factory.makeSourcePackageName('mouse')
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        dsp = ubuntu.getSourcePackage('mouse')
        markup = (
            u'<a href="/ubuntu/+source/mouse" class="sprite package-source">'
            u'mouse in Ubuntu</a>')
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
            32, self.factory.makePerson(), '+changelog')
        self.assertThat(dsp, changelog_browses_under_limit)
        with celebrity_logged_in('admin'):
            for i in range(5):
                self.factory.makePackageDiff(
                    to_source=spph.sourcepackagerelease)
        self.assertThat(dsp, changelog_browses_under_limit)


class TestDistributionSourceView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistributionSourceView, self).setUp()
        sourcepackagename = self.factory.makeSourcePackageName('mouse')
        distro = self.factory.makeDistribution()
        self.dsp = distro.getSourcePackage('mouse')

    def test_bugs_answers_usage_none(self):
        # The dict values are all False.
        view = create_view(self.dsp, '+index')
        self.assertFalse(view.bugs_answers_usage['uses_bugs'])
        self.assertFalse(view.bugs_answers_usage['uses_answers'])
        self.assertFalse(view.bugs_answers_usage['uses_both'])
        self.assertFalse(view.bugs_answers_usage['uses_either'])

    def test_bugs_answers_usage_bugs(self):
        # The dict values are True for bugs and either.
        with celebrity_logged_in('admin'):
            self.dsp.distribution.official_malone = True
        view = create_view(self.dsp, '+index')
        self.assertTrue(view.bugs_answers_usage['uses_bugs'])
        self.assertFalse(view.bugs_answers_usage['uses_answers'])
        self.assertFalse(view.bugs_answers_usage['uses_both'])
        self.assertTrue(view.bugs_answers_usage['uses_either'])

    def test_bugs_answers_usage_answers(self):
        # The dict values are True for answers and either.
        with celebrity_logged_in('admin'):
            self.dsp.distribution.answers_usage = ServiceUsage.LAUNCHPAD
        view = create_view(self.dsp, '+index')
        self.assertFalse(view.bugs_answers_usage['uses_bugs'])
        self.assertTrue(view.bugs_answers_usage['uses_answers'])
        self.assertFalse(view.bugs_answers_usage['uses_both'])
        self.assertIs(True, view.bugs_answers_usage['uses_either'])

    def test_bugs_answers_usage_both(self):
        # The dict values are all True.
        with celebrity_logged_in('admin'):
            self.dsp.distribution.official_malone = True
            self.dsp.distribution.answers_usage = ServiceUsage.LAUNCHPAD
        view = create_view(self.dsp, '+index')
        self.assertTrue(view.bugs_answers_usage['uses_bugs'])
        self.assertTrue(view.bugs_answers_usage['uses_answers'])
        self.assertTrue(view.bugs_answers_usage['uses_both'])
        self.assertTrue(view.bugs_answers_usage['uses_either'])
