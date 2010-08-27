# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the initialise_distroseries script machinery."""

__metaclass__ = type

import os
import subprocess
import sys

import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.packageset import IPackagesetSet
from lp.soyuz.enums import SourcePackageFormat
from lp.soyuz.model.distroarchseries import DistroArchSeries
from lp.soyuz.scripts.initialise_distroseries import (
    InitialisationError,
    InitialiseDistroSeries,
    )
from lp.testing import TestCaseWithFactory


class TestInitialiseDistroSeries(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestInitialiseDistroSeries, self).setUp()
        login("foo.bar@canonical.com")
        distribution_set = getUtility(IDistributionSet)
        self.ubuntutest = distribution_set['ubuntutest']
        self.ubuntu = distribution_set['ubuntu']
        self.hoary = self.ubuntu['hoary']

    def _create_distroseries(self, parent_series):
        return self.ubuntutest.newSeries(
            'foobuntu', 'FooBuntu', 'The Foobuntu', 'yeck', 'doom',
            '888', parent_series, self.hoary.owner)

    def _set_pending_to_failed(self, distroseries):
        pending_builds = distroseries.getBuildRecords(
            BuildStatus.NEEDSBUILD, pocket=PackagePublishingPocket.RELEASE)
        for build in pending_builds:
            build.status = BuildStatus.FAILEDTOBUILD

    def test_failure_with_no_parent_series(self):
        # Initialising a new distro series requires a parent series to be set
        foobuntu = self._create_distroseries(None)
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaisesWithContent(
            InitialisationError, "Parent series required.", ids.check)

    def test_failure_for_already_released_distroseries(self):
        # Initialising a distro series that has already been used will error
        ids = InitialiseDistroSeries(self.ubuntutest['breezy-autotest'])
        self.assertRaisesWithContent(
            InitialisationError,
            "Can not copy distroarchseries from parent, there are already "
            "distroarchseries(s) initialised for this series.", ids.check)

    def test_failure_with_pending_builds(self):
        # If the parent series has pending builds, we can't initialise
        foobuntu = self._create_distroseries(self.hoary)
        transaction.commit()
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaisesWithContent(
            InitialisationError, "Parent series has pending builds.",
            ids.check)

    def test_failure_with_queue_items(self):
        # If the parent series has items in its queues, such as NEW and
        # UNAPPROVED, we can't initialise
        foobuntu = self._create_distroseries(
            self.ubuntu['breezy-autotest'])
        ids = InitialiseDistroSeries(foobuntu)
        self.assertRaisesWithContent(
            InitialisationError, "Parent series queues are not empty.",
            ids.check)

    def assertDistroSeriesInitialisedCorrectly(self, foobuntu):
        # Check that 'pmount' has been copied correctly
        hoary_pmount_pubs = self.hoary.getPublishedSources('pmount')
        foobuntu_pmount_pubs = foobuntu.getPublishedSources('pmount')
        self.assertEqual(
            hoary_pmount_pubs.count(),
            foobuntu_pmount_pubs.count())
        hoary_i386_pmount_pubs = self.hoary['i386'].getReleasedPackages(
            'pmount')
        foobuntu_i386_pmount_pubs = foobuntu['i386'].getReleasedPackages(
            'pmount')
        self.assertEqual(
            len(hoary_i386_pmount_pubs), len(foobuntu_i386_pmount_pubs))
        # And the binary package, and linked source package look fine too
        pmount_binrel = (
            foobuntu['i386'].getReleasedPackages(
            'pmount')[0].binarypackagerelease)
        self.assertEqual(pmount_binrel.title, u'pmount-0.1-1')
        self.assertEqual(pmount_binrel.build.id, 7)
        self.assertEqual(
            pmount_binrel.build.title,
            u'i386 build of pmount 0.1-1 in ubuntu hoary RELEASE')
        pmount_srcrel = pmount_binrel.build.source_package_release
        self.assertEqual(pmount_srcrel.title, u'pmount - 0.1-1')
        # The build of pmount 0.1-1 has been copied across.
        foobuntu_pmount = pmount_srcrel.getBuildByArch(
            foobuntu['i386'], foobuntu.main_archive)
        hoary_pmount = pmount_srcrel.getBuildByArch(
            self.hoary['i386'], self.hoary.main_archive)
        self.assertEqual(foobuntu_pmount.id, hoary_pmount.id)
        # We also inherient the permitted source formats from our parent
        self.assertTrue(
            foobuntu.isSourcePackageFormatPermitted(
            SourcePackageFormat.FORMAT_1_0))

    def _full_initialise(self):
        foobuntu = self._create_distroseries(self.hoary)
        self._set_pending_to_failed(self.hoary)
        transaction.commit()
        ids = InitialiseDistroSeries(foobuntu)
        ids.check()
        ids.initialise()
        return foobuntu

    def test_initialise(self):
        # Test a full initialise with no errors
        foobuntu = self._full_initialise()
        self.assertDistroSeriesInitialisedCorrectly(foobuntu)

    def test_initialise_only_i386(self):
        # Test a full initialise with no errors, but only copy i386 to
        # the child
        foobuntu = self._create_distroseries(self.hoary)
        self._set_pending_to_failed(self.hoary)
        transaction.commit()
        ids = InitialiseDistroSeries(foobuntu, ('i386', ))
        ids.check()
        ids.initialise()
        self.assertDistroSeriesInitialisedCorrectly(foobuntu)
        store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)
        das = list(store.find(DistroArchSeries, distroseries = foobuntu))
        self.assertEqual(len(das), 1)
        self.assertEqual(das[0].architecturetag, 'i386')

    def test_check_no_builds(self):
        # Test that there is no build for pmount 0.1-2 in the
        # newly-initialised series.
        foobuntu = self._full_initialise()
        pmount_source = self.hoary.getSourcePackage(
            'pmount').currentrelease
        self.assertEqual(
            pmount_source.title,
            '"pmount" 0.1-2 source package in The Hoary Hedgehog Release')
        pmount_source = foobuntu.getSourcePackage('pmount').currentrelease
        self.assertEqual(
            pmount_source.title,
            '"pmount" 0.1-2 source package in The Foobuntu')
        self.assertEqual(
            pmount_source.sourcepackagerelease.getBuildByArch(
            foobuntu['i386'], foobuntu.main_archive), None)
        self.assertEqual(
            pmount_source.sourcepackagerelease.getBuildByArch(
            foobuntu['hppa'], foobuntu.main_archive), None)

    def test_create_builds(self):
        # It turns out the sampledata of hoary includes pmount 0.1-1 as well
        # as pmount 0.1-2 source, and if foobuntu and hoary don't share a
        # pool, 0.1-1 will be marked as NBS and removed. So let's check that
        # builds can be created for foobuntu.
        foobuntu = self._full_initialise()
        pmount_source = foobuntu.getSourcePackage('pmount').currentrelease
        created_build = pmount_source.sourcepackagerelease.createBuild(
            foobuntu['i386'], PackagePublishingPocket.RELEASE,
            foobuntu.main_archive)
        retrieved_build = pmount_source.sourcepackagerelease.getBuildByArch(
            foobuntu['i386'], foobuntu.main_archive)
        self.assertEqual(retrieved_build.id, created_build.id)
        self.assertEqual(
            'i386 build of pmount 0.1-2 in ubuntutest foobuntu RELEASE',
            created_build.title)

    def test_copying_packagesets(self):
        # If a parent series has packagesets, we should copy them
        uploader = self.factory.makePerson()
        test1 = getUtility(IPackagesetSet).new(
            u'test1', u'test 1 packageset', self.hoary.owner,
            distroseries=self.hoary)
        test2 = getUtility(IPackagesetSet).new(
            u'test2', u'test 2 packageset', self.hoary.owner,
            distroseries=self.hoary)
        test3 = getUtility(IPackagesetSet).new(
            u'test3', u'test 3 packageset', self.hoary.owner,
            distroseries=self.hoary, related_set=test2)
        test1.addSources('pmount')
        getUtility(IArchivePermissionSet).newPackagesetUploader(
            self.hoary.main_archive, uploader, test1)
        foobuntu = self._full_initialise()
        # We can fetch the copied sets from foobuntu
        foobuntu_test1 = getUtility(IPackagesetSet).getByName(
            u'test1', distroseries=foobuntu)
        foobuntu_test2 = getUtility(IPackagesetSet).getByName(
            u'test2', distroseries=foobuntu)
        foobuntu_test3 = getUtility(IPackagesetSet).getByName(
            u'test3', distroseries=foobuntu)
        # And we can see they are exact copies, with the related_set for the
        # copies pointing to the packageset in the parent
        self.assertEqual(test1.description, foobuntu_test1.description)
        self.assertEqual(test2.description, foobuntu_test2.description)
        self.assertEqual(test3.description, foobuntu_test3.description)
        self.assertEqual(foobuntu_test1.relatedSets().one(), test1)
        self.assertEqual(
            list(foobuntu_test2.relatedSets()),
            [test2, test3, foobuntu_test3])
        self.assertEqual(
            list(foobuntu_test3.relatedSets()),
            [test2, foobuntu_test2, test3])
        # The contents of the packagesets will have been copied.
        foobuntu_srcs = foobuntu_test1.getSourcesIncluded(
            direct_inclusion=True)
        hoary_srcs = test1.getSourcesIncluded(direct_inclusion=True)
        self.assertEqual(foobuntu_srcs, hoary_srcs)
        # The uploader can also upload to the new distroseries.
        self.assertTrue(
            getUtility(IArchivePermissionSet).isSourceUploadAllowed(
                self.hoary.main_archive, 'pmount', uploader,
                distroseries=self.hoary))
        self.assertTrue(
            getUtility(IArchivePermissionSet).isSourceUploadAllowed(
                foobuntu.main_archive, 'pmount', uploader,
                distroseries=foobuntu))

    def test_script(self):
        # Do an end-to-end test using the command-line tool
        foobuntu = self._create_distroseries(self.hoary)
        self._set_pending_to_failed(self.hoary)
        transaction.commit()
        ifp = os.path.join(
            config.root, 'scripts', 'ftpmaster-tools',
            'initialise-from-parent.py')
        process = subprocess.Popen(
            [sys.executable, ifp, "-vv", "-d", "ubuntutest", "foobuntu"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        self.assertEqual(process.returncode, 0)
        self.assertTrue(
            "DEBUG   Committing transaction." in stderr.split('\n'))
        self.assertDistroSeriesInitialisedCorrectly(foobuntu)
