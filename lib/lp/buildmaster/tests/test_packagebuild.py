# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

import unittest
import hashlib

from storm.store import Store
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.testing.layers import LaunchpadFunctionalLayer

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSet, IPackageBuildSource)
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.buildmaster.tests.test_buildbase import TestBuildBaseMixin
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import login, login_person, TestCaseWithFactory


class TestPackageBuildBase(TestCaseWithFactory):
    """Provide a factory method for creating PackageBuilds.

    This is not included in the launchpad test factory because
    only classes deriving from PackageBuild should be used.
    """

    def makePackageBuild(
        self, archive=None, job_type=BuildFarmJobType.PACKAGEBUILD,
        status=BuildStatus.NEEDSBUILD,
        pocket=PackagePublishingPocket.RELEASE):
        if archive is None:
            archive = self.factory.makeArchive()

        return getUtility(IPackageBuildSource).new(
            job_type=job_type, virtualized=True, archive=archive,
            status=status, pocket=pocket)


class TestBuildBaseMethods(TestPackageBuildBase, TestBuildBaseMixin):
    """The new PackageBuild class provides the same methods as the BuildBase.

    XXX 2010-04-21 michael.nelson bug=567922.
    Until the BuildBase class and its tests are removed, we re-use the tests
    here to ensure that there is no divergence. Once BuildBase is removed the
    tests can be moved into TestPackageBuild.
    """
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestBuildBaseMethods, self).setUp()
        self.package_build = self.makePackageBuild()


class TestPackageBuild(TestPackageBuildBase):
    """Tests for the package build object."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create a package build with which to test."""
        super(TestPackageBuild, self).setUp()
        joe = self.factory.makePerson(name="joe")
        joes_ppa = self.factory.makeArchive(owner=joe, name="ppa")
        self.package_build = self.makePackageBuild(archive=joes_ppa)

    def test_providesInterface(self):
        # PackageBuild provides IPackageBuild
        self.assertProvides(self.package_build, IPackageBuild)

    def test_saves_record(self):
        # A package build can be stored in the database.
        store = Store.of(self.package_build)
        store.flush()
        retrieved_build = store.find(
            PackageBuild,
            PackageBuild.id == self.package_build.id).one()
        self.assertEqual(self.package_build, retrieved_build)

    def test_unimplemented_methods(self):
        # Classes deriving from PackageBuild must provide getTitle.
        self.assertRaises(NotImplementedError, self.package_build.getTitle)
        self.assertRaises(
            NotImplementedError, self.package_build.estimateDuration)
        self.assertRaises(
            NotImplementedError, self.package_build.verifySuccessfulUpload)
        self.assertRaises(NotImplementedError, self.package_build.notify)
        self.assertRaises(
            NotImplementedError, self.package_build.handleStatus,
            None, None, None)

    def test_default_values(self):
        # PackageBuild has a number of default values.
        self.failUnlessEqual('buildd', self.package_build.policy_name)
        self.failUnlessEqual(
            'multiverse', self.package_build.current_component.name)
        self.failUnlessEqual(None, self.package_build.distribution)
        self.failUnlessEqual(None, self.package_build.distro_series)

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

    def test_storeUploadLog(self):
        # The given content is uploaded to the librarian and linked as
        # the upload log.
        self.package_build.storeUploadLog("Some content")
        self.failIfEqual(None, self.package_build.upload_log)
        self.failUnlessEqual(
            hashlib.sha1("Some content").hexdigest(),
            self.package_build.upload_log.content.sha1)

    def test_storeUploadLog_private(self):
        # A private package build will store the upload log on the
        # restricted librarian.
        login('admin@canonical.com')
        self.package_build.archive.buildd_secret = 'sekrit'
        self.package_build.archive.private = True
        self.failUnless(self.package_build.is_private)
        self.package_build.storeUploadLog("Some content")
        self.failUnless(self.package_build.upload_log.restricted)

    def test_upload_log_url(self):
        # The url of the upload log file is determined by the PackageBuild.
        Store.of(self.package_build).flush()
        build_id = self.package_build.build_farm_job.id
        self.package_build.storeUploadLog("Some content")
        log_url = self.package_build.upload_log_url
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/ppa/+build/%d/+files/upload_%d_log.txt' % (
                build_id, build_id),
            log_url)

    def test_view_package_build(self):
        # Anonymous access can read public builds, but not edit.
        self.failUnlessEqual(
            None, self.package_build.dependencies)
        self.assertRaises(
            Unauthorized, setattr, self.package_build,
            'dependencies', u'my deps')

    def test_edit_package_build(self):
        # An authenticated user who belongs to the owning archive team
        # can edit the build.
        login_person(self.package_build.archive.owner)
        self.package_build.dependencies = u'My deps'
        self.failUnlessEqual(
            u'My deps', self.package_build.dependencies)

        # But other users cannot.
        other_person = self.factory.makePerson()
        login_person(other_person)
        self.assertRaises(
            Unauthorized, setattr, self.package_build,
            'dependencies', u'my deps')


    def test_admin_package_build(self):
        # Users with edit access can update attributes.
        login('admin@canonical.com')
        self.package_build.dependencies = u'My deps'
        self.failUnlessEqual(
            u'My deps', self.package_build.dependencies)


class TestPackageBuildSet(TestPackageBuildBase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPackageBuildSet, self).setUp()
        person = self.factory.makePerson()
        self.archive = self.factory.makeArchive(owner=person)
        self.package_builds = []
        self.package_builds.append(
            self.makePackageBuild(archive=self.archive,
                                  pocket=PackagePublishingPocket.UPDATES))
        self.package_builds.append(
            self.makePackageBuild(archive=self.archive,
                                  status=BuildStatus.BUILDING))
        self.package_build_set = getUtility(IPackageBuildSet)

    def test_getBuildsForArchive_all(self):
        # The default call without arguments returns all builds for the
        # archive.
        self.assertContentEqual(
            self.package_builds, self.package_build_set.getBuildsForArchive(
                self.archive))

    def test_getBuildsForArchive_by_status(self):
        # If the status arg is used, the results will be filtered by
        # status.
        self.assertContentEqual(
            self.package_builds[1:],
            self.package_build_set.getBuildsForArchive(
                self.archive, status=BuildStatus.BUILDING))

    def test_getBuildsForArchive_by_pocket(self):
        # If the pocket arg is used, the results will be filtered by
        # pocket.
        self.assertContentEqual(
            self.package_builds[:1],
            self.package_build_set.getBuildsForArchive(
                self.archive, pocket=PackagePublishingPocket.UPDATES))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
