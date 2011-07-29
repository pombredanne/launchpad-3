# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the lp.soyuz.browser.builder module."""

__metaclass__ = type

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory
from lp.testing.publication import test_traverse


class TestBuildersNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_buildjob_redirects_for_recipe_build(self):
        # /builders/+buildjob/<job id> redirects to the build page.
        build = self.factory.makeSourcePackageRecipeBuild()
        url = 'http://launchpad.dev/builders/+buildjob/%s' % (
            build.build_farm_job.id)
        context, view, request = test_traverse(url)
        view()
        self.assertEqual(301, request.response.getStatus())
        self.assertEqual(
            canonical_url(build),
            request.response.getHeader('location'))

    def test_buildjob_redirects_for_binary_build(self):
        # /builders/+buildjob/<job id> redirects to the build page.
        build = self.factory.makeBinaryPackageBuild()
        url = 'http://launchpad.dev/builders/+buildjob/%s' % (
            build.build_farm_job.id)
        context, view, request = test_traverse(url)
        view()
        self.assertEqual(301, request.response.getStatus())
        self.assertEqual(
            canonical_url(build),
            request.response.getHeader('location'))
