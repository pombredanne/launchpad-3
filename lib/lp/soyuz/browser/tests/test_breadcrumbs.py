# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)
from lp.registry.interfaces.distribution import IDistributionSet


class TestDistroArchSeriesBreadcrumb(BaseBreadcrumbTestCase):

    def setUp(self):
        super(TestDistroArchSeriesBreadcrumb, self).setUp()
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.hoary = self.ubuntu.getSeries('hoary')
        self.hoary_i386 = self.hoary['i386']
        self.traversed_objects = [
            self.root, self.ubuntu, self.hoary, self.hoary_i386]

    def test_distroarchseries(self):
        das_url = canonical_url(self.hoary_i386)
        urls = self._getBreadcrumbsURLs(das_url, self.traversed_objects)
        texts = self._getBreadcrumbsTexts(das_url, self.traversed_objects)

        self.assertEquals(urls[-1], das_url)
        self.assertEquals(texts[-1], "i386")

    def test_distroarchseriesbinarypackage(self):
        pmount_hoary_i386 = self.hoary_i386.getBinaryPackage("pmount")
        self.traversed_objects.append(pmount_hoary_i386)
        pmount_url = canonical_url(pmount_hoary_i386)
        urls = self._getBreadcrumbsURLs(pmount_url, self.traversed_objects)
        texts = self._getBreadcrumbsTexts(pmount_url, self.traversed_objects)

        self.assertEquals(urls[-1], pmount_url)
        self.assertEquals(texts[-1], "pmount")

    def test_distroarchseriesbinarypackagerelease(self):
        pmount_hoary_i386 = self.hoary_i386.getBinaryPackage("pmount")
        pmount_release = pmount_hoary_i386['0.1-1']
        self.traversed_objects.extend([pmount_hoary_i386, pmount_release])
        pmount_release_url = canonical_url(pmount_release)
        urls = self._getBreadcrumbsURLs(
            pmount_release_url, self.traversed_objects)
        texts = self._getBreadcrumbsTexts(
            pmount_release_url, self.traversed_objects)

        self.assertEquals(urls[-1], pmount_release_url)
        self.assertEquals(texts[-1], "0.1-1")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
