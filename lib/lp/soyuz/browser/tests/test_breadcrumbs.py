# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.webapp.tests.breadcrumbs import (
    BaseBreadcrumbTestCase)
from lp.registry.interfaces.distribution import IDistributionSet
from lp.testing import ANONYMOUS, login


class TestDistroArchSeriesBreadcrumb(BaseBreadcrumbTestCase):

    def setUp(self):
        super(TestDistroArchSeriesBreadcrumb, self).setUp()
        self.ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
        self.hoary = self.ubuntu.getSeries('hoary')
        self.hoary_i386 = self.hoary['i386']
        self.das_url = canonical_url(self.hoary_i386)
        self.traversed_objects = [
            self.root, self.ubuntu, self.hoary, self.hoary_i386]

    def test_distroarchseries(self):
        urls = self._getBreadcrumbsURLs(self.das_url, self.traversed_objects)
        self.assertEquals(urls[-1], self.das_url)
        texts = self._getBreadcrumbsTexts(
            self.das_url, self.traversed_objects)
        self.assertEquals(texts[-1], "i386")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
