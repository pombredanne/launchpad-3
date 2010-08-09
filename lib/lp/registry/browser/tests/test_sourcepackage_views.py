# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SourcePackage view code."""

__metaclass__ = type

import cgi
import urllib

from zope.component import getUtility

from canonical.testing import DatabaseFunctionalLayer

from lp.registry.browser.sourcepackage import get_register_upstream_url
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestSourcePackageViewHelpers(TestCaseWithFactory):
    """Tests for SourcePackage view helper functions."""

    layer = DatabaseFunctionalLayer

    def test_get_register_upstream_url_displayname(self):
        source_package = self.factory.makeSourcePackage(
            sourcepackagename='python-super-package')
        return_url = 'http://example.com/foo?a=b&c=d'
        url = get_register_upstream_url(source_package, return_url)
        expected_url = (
            '/projects/+new?'
            '_return_url='
            'http%3A%2F%2Fexample.com%2Ffoo%3Fa%3Db%26c%3Dd'
            '&field.__visited_steps__=projectaddstep1'
            '&field.actions.continue=Continue'
            # The sourcepackagename 'python-super-package' is split on
            # the hyphens, and each word is capitalized.
            '&field.displayname=Python+Super+Package'
            '&field.name=python-super-package'
            # The summary is empty, since the source package doesn't
            # have a binary package release.
            '&field.summary='
            '&field.title=Python+Super+Package')
        self.assertEqual(expected_url, url)

    def test_get_register_upstream_url_summary(self):
        test_publisher = SoyuzTestPublisher()
        test_data = test_publisher.makeSourcePackageWithBinaryPackageRelease()
        source_package_name = (
            test_data['source_package'].sourcepackagename.name)
        distroseries_id = test_data['distroseries'].id
        test_publisher.updateDistroSeriesPackageCache(
            test_data['distroseries'])

        # updateDistroSeriesPackageCache reconnects the db, so the
        # objects need to be reloaded.
        distroseries = getUtility(IDistroSeriesSet).get(distroseries_id)
        source_package = distroseries.getSourcePackage(source_package_name)
        return_url = 'http://example.com/foo?a=b&c=d'
        url = get_register_upstream_url(source_package, return_url)
        expected_base = '/projects/+new'
        expected_params = [
            ('_return_url', 'http://example.com/foo?a=b&c=d'),
            ('field.__visited_steps__', 'projectaddstep1'),
            ('field.actions.continue', 'Continue'),
            ('field.displayname', 'Bonkers'),
            ('field.name', 'bonkers'),
            ('field.summary', 'summary for flubber-bin\n'
                              + 'summary for flubber-lib'),
            ('field.title', 'Bonkers'),
            ]
        base, query = urllib.splitquery(url)
        params = cgi.parse_qsl(query)
        self.assertEqual((expected_base, expected_params),
                         (base, params))

    def test_get_register_upstream_url_summary_duplicates(self):

        class FakeDistroSeriesBinaryPackage:
            def __init__(self, summary):
                self.summary = summary

        class FakeDistributionSourcePackageRelease:
            sample_binary_packages = [
                FakeDistroSeriesBinaryPackage('summary for foo'),
                FakeDistroSeriesBinaryPackage('summary for bar'),
                FakeDistroSeriesBinaryPackage('summary for baz'),
                FakeDistroSeriesBinaryPackage('summary for baz'),
                ]

        class FakeSourcePackage:
            name = 'foo'
            releases = [FakeDistributionSourcePackageRelease()]

        source_package = FakeSourcePackage()
        return_url = 'http://example.com/foo?a=b&c=d'
        url = get_register_upstream_url(source_package, return_url)
        expected_base = '/projects/+new'
        expected_params = [
            ('_return_url', 'http://example.com/foo?a=b&c=d'),
            ('field.__visited_steps__', 'projectaddstep1'),
            ('field.actions.continue', 'Continue'),
            ('field.displayname', 'Foo'),
            ('field.name', 'foo'),
            ('field.summary', 'summary for bar\n'
                              + 'summary for baz\n'
                              + 'summary for foo'),
            ('field.title', 'Foo'),
            ]
        base, query = urllib.splitquery(url)
        params = cgi.parse_qsl(query)
        self.assertEqual((expected_base, expected_params),
                         (base, params))
