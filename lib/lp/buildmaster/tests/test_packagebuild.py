# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

import unittest

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

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

    def setUp(self):
        """Create a package build with which to test."""
        super(TestPackageBuild, self).setUp()
        joe = self.factory.makePerson(name="joe")
        joes_ppa = self.factory.makeArchive(owner=joe)
        self.package_build = self.makePackageBuild(archive=joes_ppa)

    def makePackageBuild(self, archive=None):
        if archive is None:
            archive = self.factory.makeArchive()

        return getUtility(IPackageBuildSource).new(
            job_type=BuildFarmJobType.PACKAGEBUILD,
            virtualized=True,
            archive=archive,
            pocket=PackagePublishingPocket.RELEASE)

    def test_providesInterface(self):
        # PackageBuild provides IPackageBuild
        self.assertProvides(self.package_build, IPackageBuild)

    def test_saves_record(self):
        # A package build can be stored in the database.
        flush_database_updates()
        store = Store.of(self.package_build)
        retrieved_build = store.find(
            PackageBuild,
            PackageBuild.id == self.package_build.id).one()
        self.assertEqual(self.package_build, retrieved_build)

    def test_getTitle_not_implemented(self):
        # Classes deriving from PackageBuild must provide getTitle.
        self.assertRaises(NotImplementedError, self.package_build.getTitle)

    def test_default_values(self):
        # PackageBuild has a number of default values.
        self.failUnlessEqual('buildd', self.package_build.policy_name)
        self.failUnlessEqual(
            'multiverse', self.package_build.current_component.name)
        self.failUnlessEqual(None, self.package_build.distribution)

    def test_log_url(self):
        # The url of the build log file is determined by the PackageBuild.
        lfa = self.factory.makeLibraryFileAlias('mybuildlog.txt')
        removeSecurityProxy(self.package_build).log = lfa
        log_url = self.package_build.log_url
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/ppa/+build/%d/+files/mybuildlog.txt' % (
                self.package_build.build_farm_job.id),
            log_url)

    def test_upload_log_url(self):
        # The url of the upload log file is determined by the PackageBuild.
        lfa = self.factory.makeLibraryFileAlias('myuploadlog.txt')
        removeSecurityProxy(self.package_build).upload_log = lfa
        log_url = self.package_build.upload_log_url
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/ppa/+build/%d/+files/myuploadlog.txt' % (
                self.package_build.build_farm_job.id),
            log_url)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
