# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SourcePackage view code."""

__metaclass__ = type

import cgi
import urllib

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.testing.pages import find_tag_by_id
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.browser.sourcepackage import (
    get_register_upstream_url,
    PackageUpstreamTracking,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import (
    IDistroSeries,
    IDistroSeriesSet,
    )
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.views import create_initialized_view


class TestSourcePackageViewHelpers(TestCaseWithFactory):
    """Tests for SourcePackage view helper functions."""

    layer = DatabaseFunctionalLayer

    def test_get_register_upstream_url_displayname(self):
        distroseries = self.factory.makeDistroRelease(
            distribution=self.factory.makeDistribution(name='zoobuntu'),
            name='walrus')
        source_package = self.factory.makeSourcePackage(
            distroseries=distroseries,
            sourcepackagename='python-super-package')
        url = get_register_upstream_url(source_package)
        expected_base = '/projects/+new'
        expected_params = [
            ('_return_url',
             'http://launchpad.dev/zoobuntu/walrus/'
             '+source/python-super-package'),
            ('field.__visited_steps__', 'projectaddstep1'),
            ('field.actions.continue', 'Continue'),
            # The sourcepackagename 'python-super-package' is split on
            # the hyphens, and each word is capitalized.
            ('field.displayname', 'Python Super Package'),
            ('field.distroseries', 'zoobuntu/walrus'),
            ('field.name', 'python-super-package'),
            # The summary is missing, since the source package doesn't
            # have a binary package release, and parse_qsl() excludes
            # empty params.
            ('field.source_package_name', 'python-super-package'),
            ('field.title', 'Python Super Package'),
            ]
        base, query = urllib.splitquery(url)
        params = cgi.parse_qsl(query)
        self.assertEqual((expected_base, expected_params),
                         (base, params))

    def test_get_register_upstream_url_summary(self):
        test_publisher = SoyuzTestPublisher()
        test_data = test_publisher.makeSourcePackageSummaryData()
        source_package_name = (
            test_data['source_package'].sourcepackagename.name)
        distroseries_id = test_data['distroseries'].id
        test_publisher.updateDistroSeriesPackageCache(
            test_data['distroseries'])

        # updateDistroSeriesPackageCache reconnects the db, so the
        # objects need to be reloaded.
        distroseries = getUtility(IDistroSeriesSet).get(distroseries_id)
        source_package = distroseries.getSourcePackage(source_package_name)
        url = get_register_upstream_url(source_package)
        expected_base = '/projects/+new'
        expected_params = [
            ('_return_url',
             'http://launchpad.dev/youbuntu/busy/+source/bonkers'),
            ('field.__visited_steps__', 'projectaddstep1'),
            ('field.actions.continue', 'Continue'),
            ('field.displayname', 'Bonkers'),
            ('field.distroseries', 'youbuntu/busy'),
            ('field.name', 'bonkers'),
            ('field.source_package_name', 'bonkers'),
            ('field.summary', 'summary for flubber-bin\n'
                              + 'summary for flubber-lib'),
            ('field.title', 'Bonkers'),
            ]
        base, query = urllib.splitquery(url)
        params = cgi.parse_qsl(query)
        self.assertEqual((expected_base, expected_params),
                         (base, params))

    def test_get_register_upstream_url_summary_duplicates(self):

        class Faker:
            # Fakes attributes easily.
            def __init__(self, **kw):
                self.__dict__.update(kw)

        class FakeSourcePackage(Faker):
            # Interface necessary for canonical_url() call in
            # get_register_upstream_url().
            implements(ISourcePackage)

        class FakeDistroSeries(Faker):
            implements(IDistroSeries)

        class FakeDistribution(Faker):
            implements(IDistribution)

        releases = Faker(sample_binary_packages=[
            Faker(summary='summary for foo'),
            Faker(summary='summary for bar'),
            Faker(summary='summary for baz'),
            Faker(summary='summary for baz'),
            ])
        source_package = FakeSourcePackage(
            name='foo',
            sourcepackagename=Faker(name='foo'),
            distroseries=FakeDistroSeries(
                name='walrus',
                distribution=FakeDistribution(name='zoobuntu')),
            releases=[releases])

        url = get_register_upstream_url(source_package)
        expected_base = '/projects/+new'
        expected_params = [
            ('_return_url',
             'http://launchpad.dev/zoobuntu/walrus/+source/foo'),
            ('field.__visited_steps__', 'projectaddstep1'),
            ('field.actions.continue', 'Continue'),
            ('field.displayname', 'Foo'),
            ('field.distroseries', 'zoobuntu/walrus'),
            ('field.name', 'foo'),
            ('field.source_package_name', 'foo'),
            ('field.summary', 'summary for bar\n'
                              + 'summary for baz\n'
                              + 'summary for foo'),
            ('field.title', 'Foo'),
            ]
        base, query = urllib.splitquery(url)
        params = cgi.parse_qsl(query)
        self.assertEqual((expected_base, expected_params),
                         (base, params))


class TestSourcePackageUpstreamConnectionsView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSourcePackageUpstreamConnectionsView, self).setUp()
        productseries = self.factory.makeProductSeries(name='1.0')
        self.milestone = self.factory.makeMilestone(
            product=productseries.product, productseries=productseries)
        distroseries = self.factory.makeDistroRelease()
        self.source_package = self.factory.makeSourcePackage(
            distroseries=distroseries, sourcepackagename='fnord')
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=self.source_package.sourcepackagename,
            distroseries=distroseries, version='1.5-0ubuntu1')
        self.source_package.setPackaging(
            productseries, productseries.product.owner)

    def makeUpstreamRelease(self, version):
        with person_logged_in(self.milestone.productseries.product.owner):
            self.milestone.name = version
            self.factory.makeProductRelease(self.milestone)

    def assertId(self, view, id_):
        element = find_tag_by_id(view.render(), id_)
        self.assertTrue(element is not None)

    def test_current_release_tracking_none(self):
        view = create_initialized_view(
            self.source_package, name='+upstream-connections')
        self.assertEqual(
            PackageUpstreamTracking.NONE, view.current_release_tracking)
        self.assertId(view, 'no-upstream-version')

    def test_current_release_tracking_current(self):
        self.makeUpstreamRelease('1.5')
        view = create_initialized_view(
            self.source_package, name='+upstream-connections')
        self.assertEqual(
            PackageUpstreamTracking.CURRENT, view.current_release_tracking)
        self.assertId(view, 'current-upstream-version')

    def test_current_release_tracking_older(self):
        self.makeUpstreamRelease('1.4')
        view = create_initialized_view(
            self.source_package, name='+upstream-connections')
        self.assertEqual(
            PackageUpstreamTracking.OLDER, view.current_release_tracking)
        self.assertId(view, 'older-upstream-version')

    def test_current_release_tracking_newer(self):
        self.makeUpstreamRelease('1.6')
        view = create_initialized_view(
            self.source_package, name='+upstream-connections')
        self.assertEqual(
            PackageUpstreamTracking.NEWER, view.current_release_tracking)
        self.assertId(view, 'newer-upstream-version')
