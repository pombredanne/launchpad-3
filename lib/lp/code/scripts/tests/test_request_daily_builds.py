# Copyright 2010-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the request_daily_builds script"""

import transaction

from lp.services.features.testing import FeatureFixture
from lp.services.scripts.tests import run_script
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.soyuz.enums import ArchivePurpose
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessAppServerLayer


class TestRequestDailyBuilds(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def setUp(self):
        super(TestRequestDailyBuilds, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_request_daily_builds(self):
        """Ensure the request_daily_builds script requests daily builds."""
        processor = self.factory.makeProcessor(supports_virtualized=True)
        distroarchseries = self.factory.makeDistroArchSeries(
            processor=processor)
        fake_chroot = self.factory.makeLibraryFileAlias(
            filename="fake_chroot.tar.gz", db_only=True)
        distroarchseries.addOrUpdateChroot(fake_chroot)
        prod_branch = self.factory.makeProductBranch()
        prod_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[prod_branch])
        prod_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=prod_branch)
        pack_branch = self.factory.makePackageBranch()
        pack_recipe = self.factory.makeSourcePackageRecipe(
            build_daily=True, is_stale=True, branches=[pack_branch])
        pack_snap = self.factory.makeSnap(
            distroseries=distroarchseries.distroseries,
            processors=[distroarchseries.processor],
            auto_build=True, is_stale=True, branch=pack_branch)
        self.assertEqual(0, prod_recipe.pending_builds.count())
        self.assertEqual(0, prod_snap.pending_builds.count())
        self.assertEqual(0, pack_recipe.pending_builds.count())
        self.assertEqual(0, pack_snap.pending_builds.count())
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/request_daily_builds.py', [])
        self.assertIn('Requested 2 daily recipe builds.', stderr)
        self.assertIn('Requested 2 automatic snap package builds.', stderr)
        self.assertEqual(1, prod_recipe.pending_builds.count())
        self.assertEqual(1, prod_snap.pending_builds.count())
        self.assertEqual(1, pack_recipe.pending_builds.count())
        self.assertEqual(1, pack_snap.pending_builds.count())
        self.assertFalse(prod_recipe.is_stale)
        self.assertFalse(prod_snap.is_stale)
        self.assertFalse(pack_recipe.is_stale)
        self.assertFalse(pack_snap.is_stale)

    def test_request_daily_builds_oops(self):
        """Ensure errors are handled cleanly."""
        archive = self.factory.makeArchive(purpose=ArchivePurpose.COPY)
        recipe = self.factory.makeSourcePackageRecipe(
            daily_build_archive=archive, build_daily=True)
        transaction.commit()
        retcode, stdout, stderr = run_script(
            'cronscripts/request_daily_builds.py', [])
        self.assertEqual(0, recipe.pending_builds.count())
        self.assertIn('Requested 0 daily recipe builds.', stderr)
        self.assertIn('Requested 0 automatic snap package builds.', stderr)
        self.oops_capture.sync()
        self.assertEqual('NonPPABuildRequest', self.oopses[0]['type'])
        self.assertEqual(
            1, len(self.oopses), "Too many OOPSes: %r" % (self.oopses,))
