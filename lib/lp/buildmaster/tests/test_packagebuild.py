# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

import hashlib

from storm.store import Store
from zope.component import getUtility
from zope.security.management import checkPermission
from zope.security.proxy import removeSecurityProxy

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild,
    IPackageBuildSet,
    IPackageBuildSource,
    )
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import LaunchpadFunctionalLayer


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


class TestPackageBuild(TestPackageBuildBase):
    """Tests for the package build object."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        """Create a package build with which to test."""
        super(TestPackageBuild, self).setUp()
        joe = self.factory.makePerson(name="joe")
        joes_ppa = self.factory.makeArchive(owner=joe, name="ppa")
        self.package_build = self.makePackageBuild(archive=joes_ppa)

    def test_saves_record(self):
        # A package build can be stored in the database.
        store = Store.of(self.package_build)
        store.flush()
        retrieved_build = store.find(
            PackageBuild,
            PackageBuild.id == self.package_build.id).one()
        self.assertEqual(self.package_build, retrieved_build)

    def test_default_values(self):
        # PackageBuild has a number of default values.
        pb = removeSecurityProxy(self.package_build)
        self.failUnlessEqual(None, pb.distribution)
        self.failUnlessEqual(None, pb.distro_series)

    def test_destroySelf_removes_BuildFarmJob(self):
        # Destroying a packagebuild also destroys the BuildFarmJob it
        # references.
        naked_build = removeSecurityProxy(self.package_build)
        store = Store.of(self.package_build)
        # Ensure build_farm_job_id is set.
        store.flush()
        build_farm_job_id = naked_build.build_farm_job_id
        naked_build.destroySelf()
        result = store.find(
            BuildFarmJob, BuildFarmJob.id == build_farm_job_id)
        self.assertIs(None, result.one())


class TestPackageBuildMixin(TestCaseWithFactory):
    """Test methods provided by PackageBuildMixin."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPackageBuildMixin, self).setUp()
        # BuildFarmJobMixin only operates as part of a concrete
        # IBuildFarmJob implementation. Here we use
        # SourcePackageRecipeBuild.
        joe = self.factory.makePerson(name="joe")
        joes_ppa = self.factory.makeArchive(owner=joe, name="ppa")
        self.package_build = self.factory.makeSourcePackageRecipeBuild(
            archive=joes_ppa)

    def test_providesInterface(self):
        # PackageBuild provides IPackageBuild
        self.assertProvides(self.package_build, IPackageBuild)

    def test_log_url(self):
        # The url of the build log file is determined by the PackageBuild.
        lfa = self.factory.makeLibraryFileAlias('mybuildlog.txt')
        removeSecurityProxy(self.package_build).log = lfa
        log_url = self.package_build.log_url
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/ppa/+recipebuild/%d/+files/mybuildlog.txt' % (
                self.package_build.id),
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

    def test_storeUploadLog_unicode(self):
        # Unicode upload logs are uploaded as UTF-8.
        unicode_content = u"Some content \N{SNOWMAN}"
        self.package_build.storeUploadLog(unicode_content)
        self.failIfEqual(None, self.package_build.upload_log)
        self.failUnlessEqual(
            hashlib.sha1(unicode_content.encode('utf-8')).hexdigest(),
            self.package_build.upload_log.content.sha1)

    def test_upload_log_url(self):
        # The url of the upload log file is determined by the PackageBuild.
        Store.of(self.package_build).flush()
        self.package_build.storeUploadLog("Some content")
        log_url = self.package_build.upload_log_url
        self.failUnlessEqual(
            'http://launchpad.dev/~joe/'
            '+archive/ppa/+recipebuild/%d/+files/upload_%d_log.txt' % (
                self.package_build.id, self.package_build.build_farm_job.id),
            log_url)

    def test_view_package_build(self):
        # Anonymous access can read public builds, but not edit.
        self.assertTrue(checkPermission('launchpad.View', self.package_build))
        self.assertFalse(checkPermission('launchpad.Edit', self.package_build))

    def test_edit_package_build(self):
        # An authenticated user who belongs to the owning archive team
        # can edit the build.
        login_person(self.package_build.archive.owner)
        self.assertTrue(checkPermission('launchpad.View', self.package_build))
        self.assertTrue(checkPermission('launchpad.Edit', self.package_build))

        # But other users cannot.
        other_person = self.factory.makePerson()
        login_person(other_person)
        self.assertTrue(checkPermission('launchpad.View', self.package_build))
        self.assertFalse(checkPermission('launchpad.Edit', self.package_build))

    def test_admin_package_build(self):
        # Users with edit access can update attributes.
        login('admin@canonical.com')
        self.assertTrue(checkPermission('launchpad.View', self.package_build))
        self.assertTrue(checkPermission('launchpad.Edit', self.package_build))


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
