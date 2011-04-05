# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for distroseries."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import (
    ANONYMOUS,
    login,
    )
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.registry.errors import NoSuchDistroSeries
from lp.registry.interfaces.distroseries import IDistroSeriesSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.distroseriessourcepackagerelease import (
    IDistroSeriesSourcePackageRelease,
    )
from lp.soyuz.interfaces.publishing import active_publishing_status
from lp.soyuz.model.processor import ProcessorFamilySet
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    person_logged_in,
    TestCase,
    TestCaseWithFactory,
    )
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )


class TestDistroSeriesCurrentSourceReleases(TestCase):
    """Test for DistroSeries.getCurrentSourceReleases()."""

    layer = LaunchpadFunctionalLayer
    release_interface = IDistroSeriesSourcePackageRelease

    def setUp(self):
        # Log in as an admin, so that we can create distributions.
        super(TestDistroSeriesCurrentSourceReleases, self).setUp()
        login('foo.bar@canonical.com')
        self.publisher = SoyuzTestPublisher()
        self.factory = self.publisher.factory
        self.development_series = self.publisher.setUpDefaultDistroSeries()
        self.distribution = self.development_series.distribution
        self.published_package = self.test_target.getSourcePackage(
            self.publisher.default_package_name)
        login(ANONYMOUS)

    @property
    def test_target(self):
        return self.development_series

    def assertCurrentVersion(self, expected_version, package_name=None):
        """Assert the current version of a package is the expected one.

        It uses getCurrentSourceReleases() to get the version.

        If package_name isn't specified, the test publisher's default
        name is used.
        """
        if package_name is None:
            package_name = self.publisher.default_package_name
        package = self.test_target.getSourcePackage(package_name)
        releases = self.test_target.getCurrentSourceReleases(
            [package.sourcepackagename])
        self.assertEqual(releases[package].version, expected_version)

    def test_one_release(self):
        # If there is one published version, that one will be returned.
        self.publisher.getPubSource(version='0.9')
        self.assertCurrentVersion('0.9')

    def test_return_value(self):
        # getCurrentSourceReleases() returns a dict. The corresponding
        # source package is used as the key, with
        # a DistroSeriesSourcePackageRelease as the values.
        self.publisher.getPubSource(version='0.9')
        releases = self.test_target.getCurrentSourceReleases(
            [self.published_package.sourcepackagename])
        self.assertTrue(self.published_package in releases)
        self.assertTrue(self.release_interface.providedBy(
            releases[self.published_package]))

    def test_latest_version(self):
        # If more than one version is published, the latest one is
        # returned.
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(version='1.0')
        self.assertCurrentVersion('1.0')

    def test_active_publishing_status(self):
        # Every status defined in active_publishing_status is considered
        # when checking for the current release.
        self.publisher.getPubSource(version='0.9')
        for minor_version, status in enumerate(active_publishing_status):
            latest_version = '1.%s' % minor_version
            self.publisher.getPubSource(version=latest_version, status=status)
            self.assertCurrentVersion(latest_version)

    def test_not_active_publishing_status(self):
        # Every status not defined in active_publishing_status is
        # ignored when checking for the current release.
        self.publisher.getPubSource(version='0.9')
        for minor_version, status in enumerate(PackagePublishingStatus.items):
            if status in active_publishing_status:
                continue
            self.publisher.getPubSource(
                version='1.%s' % minor_version, status=status)
            self.assertCurrentVersion('0.9')

    def test_ignore_other_package_names(self):
        # Packages with different names don't affect the returned
        # version.
        self.publisher.getPubSource(version='0.9', sourcename='foo')
        self.publisher.getPubSource(version='1.0', sourcename='bar')
        self.assertCurrentVersion('0.9', package_name='foo')

    def ignore_other_distributions(self):
        # Packages with the same name in other distributions don't
        # affect the returned version.
        series_in_other_distribution = self.factory.makeDistroRelease()
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(
            version='1.0', distroseries=series_in_other_distribution)
        self.assertCurrentVersion('0.9')

    def test_ignore_ppa(self):
        # PPA packages having the same name don't affect the returned
        # version.
        ppa_uploader = self.factory.makePerson()
        ppa_archive = getUtility(IArchiveSet).new(
            purpose=ArchivePurpose.PPA, owner=ppa_uploader,
            distribution=self.distribution)
        self.publisher.getPubSource(version='0.9')
        self.publisher.getPubSource(version='1.0', archive=ppa_archive)
        self.assertCurrentVersion('0.9')

    def test_get_multiple(self):
        # getCurrentSourceReleases() allows you to get information about
        # the current release for multiple packages at the same time.
        # This is done using a single DB query, making it more efficient
        # than using IDistributionSource.currentrelease.
        self.publisher.getPubSource(version='0.9', sourcename='foo')
        self.publisher.getPubSource(version='1.0', sourcename='bar')
        foo_package = self.distribution.getSourcePackage('foo')
        bar_package = self.distribution.getSourcePackage('bar')
        releases = self.distribution.getCurrentSourceReleases(
            [foo_package.sourcepackagename, bar_package.sourcepackagename])
        self.assertEqual(releases[foo_package].version, '0.9')
        self.assertEqual(releases[bar_package].version, '1.0')


class TestDistroSeries(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getSuite_release_pocket(self):
        # The suite of a distro series and the release pocket is the name of
        # the distroseries.
        distroseries = self.factory.makeDistroRelease()
        self.assertEqual(
            distroseries.name,
            distroseries.getSuite(PackagePublishingPocket.RELEASE))

    def test_getSuite_non_release_pocket(self):
        # The suite of a distro series and a non-release pocket is the name of
        # the distroseries followed by a hyphen and the name of the pocket in
        # lower case.
        distroseries = self.factory.makeDistroRelease()
        pocket = PackagePublishingPocket.PROPOSED
        suite = '%s-%s' % (distroseries.name, pocket.name.lower())
        self.assertEqual(suite, distroseries.getSuite(pocket))

    def test_getDistroArchSeriesByProcessor(self):
        # A IDistroArchSeries can be retrieved by processor
        distroseries = self.factory.makeDistroRelease()
        processorfamily = ProcessorFamilySet().getByName('x86')
        distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag='i386',
            processorfamily=processorfamily)
        self.assertEquals(distroarchseries,
            distroseries.getDistroArchSeriesByProcessor(
                processorfamily.processors[0]))

    def test_getDistroArchSeriesByProcessor_none(self):
        # getDistroArchSeriesByProcessor returns None when no distroarchseries
        # is found
        distroseries = self.factory.makeDistroRelease()
        processorfamily = ProcessorFamilySet().getByName('x86')
        self.assertIs(None,
            distroseries.getDistroArchSeriesByProcessor(
                processorfamily.processors[0]))

    def test_getDerivedSeries(self):
        distroseries = self.factory.makeDistroSeries(
            parent_series=self.factory.makeDistroSeries())
        self.assertContentEqual(
            [distroseries], distroseries.parent_series.getDerivedSeries())

    def test_registrant_owner_differ(self):
        # The registrant is the creator whereas the owner is the distribution's
        # owner
        registrant = self.factory.makePerson()
        distroseries = self.factory.makeDistroRelease(registrant=registrant)
        self.assertEquals(distroseries.distribution.owner, distroseries.owner)
        self.assertEquals(registrant, distroseries.registrant)
        self.assertNotEqual(distroseries.registrant, distroseries.owner)


class TestDistroSeriesPackaging(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroSeriesPackaging, self).setUp()
        self.series = self.factory.makeDistroRelease()
        self.user = self.series.distribution.owner
        login('admin@canonical.com')
        component_set = getUtility(IComponentSet)
        self.packages = {}
        self.main_component = component_set['main']
        self.universe_component = component_set['universe']
        self.makeSeriesPackage('normal')
        self.makeSeriesPackage('translatable', messages=800)
        hot_package = self.makeSeriesPackage('hot', heat=500)
        # Create a second SPPH for 'hot', to verify that duplicates are
        # eliminated in the queries.
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=hot_package.sourcepackagename,
            distroseries=self.series,
            component=self.universe_component, section_name='web')
        self.makeSeriesPackage('hot-translatable', heat=250, messages=1000)
        self.makeSeriesPackage('main', is_main=True)
        self.makeSeriesPackage('linked')
        self.linkPackage('linked')
        transaction.commit()
        login(ANONYMOUS)

    def makeSeriesPackage(self, name,
                          is_main=False, heat=None, messages=None,
                          is_translations=False):
        # Make a published source package.
        if is_main:
            component = self.main_component
        else:
            component = self.universe_component
        if is_translations:
            section = 'translations'
        else:
            section = 'web'
        sourcepackagename = self.factory.makeSourcePackageName(name)
        self.factory.makeSourcePackagePublishingHistory(
            sourcepackagename=sourcepackagename, distroseries=self.series,
            component=component, section_name=section)
        source_package = self.factory.makeSourcePackage(
            sourcepackagename=sourcepackagename, distroseries=self.series)
        if heat is not None:
            bugtask = self.factory.makeBugTask(
                target=source_package, owner=self.user)
            bugtask.bug.setHeat(heat)
        if messages is not None:
            template = self.factory.makePOTemplate(
                distroseries=self.series, sourcepackagename=sourcepackagename,
                owner=self.user)
            removeSecurityProxy(template).messagecount = messages
        self.packages[name] = source_package
        return source_package

    def linkPackage(self, name):
        product_series = self.factory.makeProductSeries()
        product_series.setPackaging(
            self.series, self.packages[name].sourcepackagename, self.user)
        return product_series

    def test_getPrioritizedUnlinkedSourcePackages(self):
        # Verify the ordering of source packages that need linking.
        package_summaries = self.series.getPrioritizedUnlinkedSourcePackages()
        names = [summary['package'].name for summary in package_summaries]
        expected = [
            u'main', u'hot-translatable', u'hot', u'translatable', u'normal']
        self.assertEqual(expected, names)

    def test_getPrioritizedUnlinkedSourcePackages_no_language_packs(self):
        # Verify that translations packages are not listed.
        self.makeSeriesPackage('language-pack-vi', is_translations=True)
        package_summaries = self.series.getPrioritizedUnlinkedSourcePackages()
        names = [summary['package'].name for summary in package_summaries]
        expected = [
            u'main', u'hot-translatable', u'hot', u'translatable', u'normal']
        self.assertEqual(expected, names)

    def test_getPrioritizedPackagings(self):
        # Verify the ordering of packagings that need more upstream info.
        for name in ['main', 'hot-translatable', 'hot', 'translatable']:
            self.linkPackage(name)
        packagings = self.series.getPrioritizedPackagings()
        names = [packaging.sourcepackagename.name for packaging in packagings]
        expected = [
            u'main', u'hot-translatable', u'hot', u'translatable', u'linked']
        self.assertEqual(expected, names)

    def test_getPrioritizedPackagings_bug_tracker(self):
        # Verify the ordering of packagings with and without a bug tracker.
        self.linkPackage('hot')
        self.makeSeriesPackage('cold')
        product_series = self.linkPackage('cold')
        with person_logged_in(product_series.product.owner):
            product_series.product.bugtracker = self.factory.makeBugTracker()
        packagings = self.series.getPrioritizedPackagings()
        names = [packaging.sourcepackagename.name for packaging in packagings]
        expected = [u'hot', u'linked', u'cold']
        self.assertEqual(expected, names)

    def test_getPrioritizedPackagings_branch(self):
        # Verify the ordering of packagings with and without a branch.
        self.linkPackage('translatable')
        self.makeSeriesPackage('withbranch')
        product_series = self.linkPackage('withbranch')
        with person_logged_in(product_series.product.owner):
            product_series.branch = self.factory.makeBranch()
        packagings = self.series.getPrioritizedPackagings()
        names = [packaging.sourcepackagename.name for packaging in packagings]
        expected = [u'translatable', u'linked', u'withbranch']
        self.assertEqual(expected, names)

    def test_getPrioritizedPackagings_translation(self):
        # Verify the ordering of translatable packagings that are and are not
        # configured to import.
        self.linkPackage('translatable')
        self.makeSeriesPackage('importabletranslatable')
        product_series = self.linkPackage('importabletranslatable')
        with person_logged_in(product_series.product.owner):
            product_series.branch = self.factory.makeBranch()
            product_series.translations_autoimport_mode = (
                TranslationsBranchImportMode.IMPORT_TEMPLATES)
        packagings = self.series.getPrioritizedPackagings()
        names = [packaging.sourcepackagename.name for packaging in packagings]
        expected = [u'translatable', u'linked', u'importabletranslatable']
        self.assertEqual(expected, names)


class TestDistroSeriesSet(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _get_translatables(self):
        distro_series_set = getUtility(IDistroSeriesSet)
        # Get translatables as a sequence of names of the series.
        return sorted(
            [series.name for series in distro_series_set.translatables()])

    def _ref_translatables(self, expected=None):
        # Return the reference value, merged with expected data.
        if expected is None:
            return self.ref_translatables
        if isinstance(expected, list):
            return sorted(self.ref_translatables + expected)
        return sorted(self.ref_translatables + [expected])

    def test_translatables(self):
        # translatables() returns all distroseries that have potemplates
        # and are not set to "hide all translations".
        # See whatever distroseries sample data already has.
        self.ref_translatables = self._get_translatables()

        new_distroseries = (
            self.factory.makeDistroRelease(name=u"sampleseries"))
        with person_logged_in(new_distroseries.distribution.owner):
            new_distroseries.hide_all_translations = False
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(),
            "A newly created distroseries should not be translatable but "
            "translatables() returns %r instead of %r." % (
                translatables, self._ref_translatables()))

        new_sourcepackagename = self.factory.makeSourcePackageName()
        self.factory.makePOTemplate(
            distroseries=new_distroseries,
            sourcepackagename=new_sourcepackagename)
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(u"sampleseries"),
            "After assigning a PO template, a distroseries should be "
            "translatable but translatables() returns %r instead of %r." % (
                translatables,
                self._ref_translatables(u"sampleseries")))

        with person_logged_in(new_distroseries.distribution.owner):
            new_distroseries.hide_all_translations = True
        transaction.commit()
        translatables = self._get_translatables()
        self.failUnlessEqual(
            translatables, self._ref_translatables(),
            "After hiding all translation, a distroseries should not be "
            "translatable but translatables() returns %r instead of %r." % (
                translatables, self._ref_translatables()))

    def test_fromSuite_release_pocket(self):
        series = self.factory.makeDistroRelease()
        result = getUtility(IDistroSeriesSet).fromSuite(
            series.distribution, series.name)
        self.assertEqual((series, PackagePublishingPocket.RELEASE), result)

    def test_fromSuite_non_release_pocket(self):
        series = self.factory.makeDistroRelease()
        suite = '%s-backports' % series.name
        result = getUtility(IDistroSeriesSet).fromSuite(
            series.distribution, suite)
        self.assertEqual((series, PackagePublishingPocket.BACKPORTS), result)

    def test_fromSuite_no_such_series(self):
        distribution = self.factory.makeDistribution()
        self.assertRaises(
            NoSuchDistroSeries,
            getUtility(IDistroSeriesSet).fromSuite,
            distribution, 'doesntexist')
