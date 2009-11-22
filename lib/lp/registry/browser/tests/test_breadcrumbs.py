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
        self.assertEquals(
            last_crumb.text, self.distroseries.named_version)


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
        self.assertEquals(
            last_crumb.text, displayname)

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
        self.assertEquals(
            last_crumb.text, "Example.com-archive")

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
        self.assertEquals(
            last_crumb.text, "Example.com-archive")


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
        self.assertEquals(
            last_crumb.text, self.poll.title)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
