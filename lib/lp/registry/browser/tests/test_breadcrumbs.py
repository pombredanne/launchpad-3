# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)
from lp.registry.interfaces.distributionmirror import (
    MirrorContent, MirrorSpeed)
from lp.services.worlddata.interfaces.country import ICountrySet


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
        self.distribution_url = canonical_url(self.distribution)

    def _makeMirror(self, displayname, http_url=None, ftp_url=None,
                    rsync_url=None):
        """Create a mirror for the distribution."""
        # If no URL is specified create an HTTP URL.
        if http_url is None and ftp_url is None and rsync_url is None:
            http_url = self.factory.getUniqueURL()
        argentina = getUtility(ICountrySet)['AR']

        mirror = self.distribution.newMirror(
            owner=self.distribution.owner,
            speed=MirrorSpeed.S256K,
            country=argentina,
            content=MirrorContent.ARCHIVE,
            displayname=displayname,
            description=None,
            http_base_url=http_url,
            ftp_base_url=ftp_url,
            rsync_base_url=rsync_url,
            official_candidate=False)
        return (mirror, canonical_url(mirror))

    def test_distributionmirror_withDisplayName(self):
        # If a displayname is given, the breadcrumb text will be the
        # displayname.
        displayname = "Akbar and Jeff's Hut of Mirrors"
        mirror, mirror_url = self._makeMirror(
            displayname=displayname)
        crumbs = self._getBreadcrumbs(
            mirror_url,
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEquals(
            last_crumb.text, displayname)

    def test_distributionmirror_withHttpUrl(self):
        # If no displayname, the breadcrumb text will be the mirror name,
        # which is derived from the URL.
        http_url = "http://example.com/akbar"
        mirror, mirror_url = self._makeMirror(
            displayname=None,
            http_url=http_url)
        crumbs = self._getBreadcrumbs(
            mirror_url,
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEquals(
            last_crumb.text, "Example.com-archive")

    def test_distributionmirror_withFtpUrl(self):
        # If no displayname, the breadcrumb text will be the mirror name,
        # which is derived from the URL.
        ftp_url = "ftp://example.com/jeff"
        mirror, mirror_url = self._makeMirror(
            displayname=None,
            ftp_url=ftp_url)
        crumbs = self._getBreadcrumbs(
            mirror_url,
            [self.root, self.distribution, mirror])
        last_crumb = crumbs[-1]
        self.assertEquals(
            last_crumb.text, "Example.com-archive")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
