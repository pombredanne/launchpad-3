# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test initializing a distroseries using
IDistroSeries.initDerivedDistroSeries."""

__metaclass__ = type

import transaction
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.interfaces.distroseries import DerivationError
from lp.services.features.testing import FeatureFixture
from lp.soyuz.enums import PackageUploadStatus
from lp.soyuz.interfaces.distributionjob import (
    IInitializeDistroSeriesJobSource,
    )
from lp.soyuz.model.distroseriesdifferencejob import (
    FEATURE_FLAG_ENABLE_MODULE,
    )
from lp.soyuz.scripts.tests.test_initialize_distroseries import (
    InitializationHelperTestCase,
    )
from lp.testing import (
    ANONYMOUS,
    login,
    login_person,
    TestCaseWithFactory,
    )


class TestDeriveDistroSeries(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestDeriveDistroSeries, self).setUp()
        self.parent = self.factory.makeDistroSeries()
        self.child = self.factory.makeDistroSeries()
        removeSecurityProxy(self.child).driver = self.factory.makePerson()
        login_person(self.child.driver)

    def test_no_permission_to_call(self):
        login(ANONYMOUS)
        self.assertRaises(
            Unauthorized, getattr, self.child, "initDerivedDistroSeries")

    def test_parent_is_not_set(self):
        # When the series already has a parent series, it means that the
        # distroseries has already been derived, and it is forbidden to
        # derive more than once.
        self.factory.makeDistroSeriesParent(
            derived_series=self.child, parent_series=self.parent)
        self.assertRaisesWithContent(
            DerivationError,
            ("DistroSeries {self.child.name} already has parent "
             "series.".format(self=self)),
            self.child.initDerivedDistroSeries, self.child.driver,
            [self.parent.id])

    def test_init_creates_new_job(self):
        self.child.initDerivedDistroSeries(
            self.child.driver, [self.parent.id])
        [job] = list(
            getUtility(IInitializeDistroSeriesJobSource).iterReady())
        self.assertEqual(job.distroseries, self.child)


class TestDeriveDistroSeriesMultipleParents(InitializationHelperTestCase):

    layer = LaunchpadZopelessLayer

    def setUpParents(self, packages1, packages2):
        parent1, unused = self.setupParent(packages=packages1)
        parent2, unused = self.setupParent(packages=packages2)
        return parent1, parent2

    def assertBinPackagesAndVersions(self, series, pack_versions):
        # Helper to assert that series contains the required binaries
        # pack_version should be of the form [(packagname1, version1), ...]
        # e.g. [(u'p1', u'0.1-1'), (u'p2', u'2.1')])
        pub_sources = series.main_archive.getPublishedSources(
            distroseries=series)
        binaries = sorted(
            [(p.getBuiltBinaries()[0].binarypackagerelease.sourcepackagename,
              p.getBuiltBinaries()[0].binarypackagerelease.version)
                 for p in pub_sources])

        self.assertEquals(pack_versions, binaries)

    def test_multiple_parents_binary_packages(self):
        # An initialization from many parents (using the package copier)
        # can happen using the same the db user the job will use
        # ('initializedistroseries').
        parent1, parent2 = self.setUpParents(
            packages1={'p1': '0.1-1'}, packages2={'p2': '2.1'})
        child = self.factory.makeDistroSeries()
        transaction.commit()
        self.layer.switchDbUser('initializedistroseries')

        child = self._fullInitialize(
            [parent1, parent2], child=child)
        self.assertBinPackagesAndVersions(
            child,
            [(u'p1', u'0.1-1'), (u'p2', u'2.1')])

    def test_multiple_parents_dsd_flag_on(self):
        # A initialization can happen if the flag for distroseries
        # difference creation is on.
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))
        parent1, parent2 = self.setUpParents(
            packages1={'p1': '0.1-1'}, packages2={'p2': '2.1'})
        child = self.factory.makeDistroSeries()
        transaction.commit()
        self.layer.switchDbUser('initializedistroseries')

        child = self._fullInitialize(
            [parent1, parent2], child=child)
        self.assertBinPackagesAndVersions(
            child,
            [(u'p1', u'0.1-1'), (u'p2', u'2.1')])
        # Switch back to launchpad_main to be able to cleanup the
        # feature flags.
        self.layer.switchDbUser('launchpad_main')

    def test_multiple_parents_close_bugs(self):
        # Even when bugs are present in the second parent, the initialization
        # does not close the bugs on the copied publications (and thus
        # does not try to access the bug table).
        self.useFixture(FeatureFixture({FEATURE_FLAG_ENABLE_MODULE: u'on'}))
        parent1, parent2 = self.setUpParents(
            packages1={'p1': '0.1-1'}, packages2={'p2': '2.1'})
        source = parent2.main_archive.getPublishedSources(
            distroseries=parent2)[0]
        # Setup a bug and populate
        # source.sourcepackagerelease.upload_changesfile.
        bug = self.factory.makeBug(series=parent2)
        changes_file_content = (
            "Format: 1.7\nLaunchpad-bugs-fixed: %s\n"
            % bug.id)
        pu = self.factory.makePackageUpload(
            archive=parent2.main_archive, distroseries=parent2,
            changes_file_content=changes_file_content,
            status=PackageUploadStatus.DONE)
        pu.addSource(source.sourcepackagerelease)
        child = self.factory.makeDistroSeries()
        transaction.commit()
        self.layer.switchDbUser('initializedistroseries')

        child = self._fullInitialize(
            [parent1, parent2], child=child)
        # Make sure the initialization was successful.
        self.assertBinPackagesAndVersions(
            child,
            [(u'p1', u'0.1-1'), (u'p2', u'2.1')])
        # Switch back to launchpad_main to be able to cleanup the
        # feature flags.
        self.layer.switchDbUser('launchpad_main')
