# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.testing.pages import get_feedback_messages
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.person import IPersonSet
from lp.soyuz.enums import PackagePublishingStatus
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import ADMIN_EMAIL


class TestBugAlsoAffectsDistribution(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugAlsoAffectsDistribution, self).setUp()
        self.admin = getUtility(IPersonSet).getByEmail(ADMIN_EMAIL)
        self.distribution = self.factory.makeDistribution()
        with person_logged_in(self.admin):
           self.distribution.official_malone = True

    def test_bug_alsoaffects_spn_exists(self):
        bug = self.factory.makeBug()
        spn = self.factory.makeSourcePackageName()
        browser = self.getUserBrowser()
        browser.open(canonical_url(bug))
        browser.getLink(url='+distrotask').click()
        browser.getControl('Distribution').value = [self.distribution.name]
        browser.getControl('Source Package Name').value = spn.name
        browser.getControl('Continue').click()
        self.assertEqual([], get_feedback_messages(browser.contents))

    def test_bug_alsoaffects_spn_not_exists_with_published_binaries(self):
        bug = self.factory.makeBug()
        distroseries = self.factory.makeDistroSeries(
            distribution=self.distribution)
        das = self.factory.makeDistroArchSeries(distroseries=distroseries)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            distroarchseries=das, status=PackagePublishingStatus.PUBLISHED)
        self.assertTrue(self.distribution.has_published_binaries)
        browser = self.getUserBrowser()
        browser.open(canonical_url(bug))
        browser.getLink(url='+distrotask').click()
        browser.getControl('Distribution').value = [self.distribution.name]
        browser.getControl('Source Package Name').value = 'does-not-exist'
        browser.getControl('Continue').click()
        expected = [
            u'There is 1 error.',
            u'There is no package in %s named "does-not-exist".' % (
                self.distribution.displayname)]
        self.assertEqual(expected, get_feedback_messages(browser.contents))

    def test_bug_alsoaffects_spn_not_exists_with_no_binaries(self):
        bug = self.factory.makeBug()
        browser = self.getUserBrowser()
        browser.open(canonical_url(bug))
        browser.getLink(url='+distrotask').click()
        browser.getControl('Distribution').value = [self.distribution.name]
        browser.getControl('Source Package Name').value = 'does-not-exist'
        browser.getControl('Continue').click()
        expected = [
            u'There is 1 error.',
            u'There is no package in %s named "does-not-exist". Launchpad '
            'does not track binary package names in %s.' % (
                self.distribution.displayname,
                self.distribution.displayname)]
        self.assertEqual(expected, get_feedback_messages(browser.contents))
