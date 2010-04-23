# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility

from canonical.database.sqlbase import flush_database_updates
from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSource)
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import TestCaseWithFactory


class TestPackageBuild(TestCaseWithFactory):
    """Tests for the package build object."""

    layer = LaunchpadFunctionalLayer

    def makePackageBuild(self):
        return getUtility(IPackageBuildSource).new(
            job_type=BuildFarmJobType.PACKAGEBUILD,
            virtualized=True,
            archive=self.factory.makeArchive(),
            pocket=PackagePublishingPocket.RELEASE)

    def test_providesInterface(self):
        # PackageBuild provides IPackageBuild
        package_build = self.makePackageBuild()
        self.assertProvides(package_build, IPackageBuild)

    def test_saves_record(self):
        # A package build can be stored in the database.
        package_build = self.makePackageBuild()
        flush_database_updates()
        store = Store.of(package_build)
        retrieved_build = store.find(
            PackageBuild,
            PackageBuild.id == package_build.id).one()
        self.assertEqual(package_build, retrieved_build)

    def test_getTitle_not_implemented(self):
        # Classes deriving from PackageBuild must provide getTitle.
        package_build = self.makePackageBuild()
        self.assertRaises(NotImplementedError, package_build.getTitle)

    def test_default_values(self):
        package_build = self.makePackageBuild()
        self.failUnlessEqual('buildd', package_build.policy_name)
        self.failUnlessEqual(
            'multiverse', package_build.current_component.name)
        self.failUnlessEqual(None, package_build.distribution)

    def test_log_url(self):
        lfa = self.factory.makeLibraryFileAlias('myfile.txt')
        import pdb;pdb.set_trace()
        self.failUnless(
            False, "Add test.")

    def test_upload_log_url(self):
        self.failUnless(False, "Add a test")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
