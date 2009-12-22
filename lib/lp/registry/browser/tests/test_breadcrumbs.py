# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)


class TestDistroseriesBreadcrumb(BaseBreadcrumbTestCase):
    """Test breadcrumbs for an `IDistroseries`."""

    def setUp(self):
        super(TestDistroseriesBreadcrumb, self).setUp()
        self.distribution = self.factory.makeDistribution(
            name='youbuntu', displayname='Youbuntu')
        self.distroseries = self.factory.makeDistroRelease(
            name='groovy', version="1.06", distribution=self.distribution)
        self.distroseries_url = canonical_url(self.distroseries)

    def test_distroseries(self):
        crumbs = self._getBreadcrumbs(
            self.distroseries_url,
            [self.root, self.distribution, self.distroseries])
        last_crumb = crumbs[-1]
        self.assertEqual(self.distroseries.named_version, last_crumb.text)


class TestDistributionMirrorBreadcrumb(BaseBreadcrumbTestCase):
    """Test breadcrumbs for an `IDistributionMirror`."""

    def setUp(self):
        super(TestDistributionMirrorBreadcrumb, self).setUp()
        self.distribution = getUtility(ILaunchpadCelebrities).ubuntu

    def test_distributionmirror_withDisplayName(self):
        # If a displayname is given, the breadcrumb text will be the
        # displayname.
        displayname = "Akbar and Jeff's Hut of Mirrors"
        mirror = self.factory.makeMirror(
            distribution=self.distribution,
            displayname=displayname)
        crumbs = self._getBreadcrumbs(
            canonical_url(mirror),
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEqual(displayname, last_crumb.text)

    def test_distributionmirror_withHttpUrl(self):
        # If no displayname, the breadcrumb text will be the mirror name,
        # which is derived from the URL.
        http_url = "http://example.com/akbar"
        mirror = self.factory.makeMirror(
            distribution=self.distribution,
            displayname=None,
            http_url=http_url)
        crumbs = self._getBreadcrumbs(
            canonical_url(mirror),
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEqual("Example.com-archive", last_crumb.text)

    def test_distributionmirror_withFtpUrl(self):
        # If no displayname, the breadcrumb text will be the mirror name,
        # which is derived from the URL.
        ftp_url = "ftp://example.com/jeff"
        mirror = self.factory.makeMirror(
            distribution=self.distribution,
            displayname=None,
            ftp_url=ftp_url)
        crumbs = self._getBreadcrumbs(
            canonical_url(mirror),
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEqual("Example.com-archive", last_crumb.text)


class TestMilestoneBreadcrumb(BaseBreadcrumbTestCase):
    """Test the breadcrumbs for an `IMilestone`."""

    def setUp(self):
        super(TestMilestoneBreadcrumb, self).setUp()
        self.project = self.factory.makeProduct()
        self.series = self.factory.makeProductSeries(product=self.project)
        self.milestone = self.factory.makeMilestone(
            productseries=self.series, name="1.1")
        self.milestone_url = canonical_url(self.milestone)

    def test_milestone_without_code_name(self):
        crumbs = self._getBreadcrumbs(
            self.milestone_url, [self.root, self.project, self.milestone])
        last_crumb = crumbs[-1]
        self.assertEqual(self.milestone.name, last_crumb.text)

    def test_milestone_with_code_name(self):
        self.milestone.code_name = "duck"
        crumbs = self._getBreadcrumbs(
            self.milestone_url, [self.root, self.project, self.milestone])
        last_crumb = crumbs[-1]
        expected_text = '%s "%s"' % (
            self.milestone.name, self.milestone.code_name)
        self.assertEqual(expected_text, last_crumb.text)

    def test_productrelease(self):
        release = self.factory.makeProductRelease(milestone=self.milestone)
        self.release_url = canonical_url(release)
        crumbs = self._getBreadcrumbs(
            self.release_url,
            [self.root, self.project, self.series, self.milestone])
        last_crumb = crumbs[-1]
        self.assertEqual(self.milestone.name, last_crumb.text)


class TestPollBreadcrumb(BaseBreadcrumbTestCase):
    """Test breadcrumbs for an `IPoll`."""

    def setUp(self):
        super(TestPollBreadcrumb, self).setUp()
        self.team = self.factory.makeTeam(displayname="Poll Team")
        name = "pollo-poll"
        title = "Marco Pollo"
        proposition = "Be mine"
        self.poll = self.factory.makePoll(
            team=self.team,
            name=name,
            title=title,
            proposition=proposition)
        self.poll_url = canonical_url(self.poll)

    def test_poll(self):
        crumbs = self._getBreadcrumbs(
            self.poll_url,
            [self.root, self.team, self.poll])
        last_crumb = crumbs[-1]
        self.assertEqual(self.poll.title, last_crumb.text)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
