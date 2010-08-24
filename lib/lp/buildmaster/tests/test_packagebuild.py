# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `IPackageBuild`."""

__metaclass__ = type

from datetime import datetime
import hashlib
import os.path

from storm.store import Store
from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild,
    IPackageBuildSet,
    IPackageBuildSource,
    )
from lp.buildmaster.model.packagebuild import PackageBuild
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.soyuz.tests.soyuzbuilddhelpers import WaitingSlave
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


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

    def test_getUploadDirLeaf(self):
        # getUploadDirLeaf returns the current time, followed by the build
        # cookie.
        now = datetime.now()
        build_cookie = self.factory.getUniqueString()
        upload_leaf = self.package_build.getUploadDirLeaf(
            build_cookie, now=now)
        self.assertEqual(
            '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_cookie),
            upload_leaf)

    def test_getUploadDir(self):
        # getUploadDir is the absolute path to the directory in which things
        # are uploaded to.
        build_cookie = self.factory.getUniqueInteger()
        upload_leaf = self.package_build.getUploadDirLeaf(build_cookie)
        upload_dir = self.package_build.getUploadDir(upload_leaf)
        self.assertEqual(
            os.path.join(config.builddmaster.root, 'incoming', upload_leaf),
            upload_dir)


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


class TestGetUploadMethodsMixin:
    """Tests for `IPackageBuild` that need objects from the rest of LP."""

    layer = LaunchpadZopelessLayer

    def makeBuild(self):
        """Allow classes to override the build with which the test runs."""
        raise NotImplemented

    def setUp(self):
        super(TestGetUploadMethodsMixin, self).setUp()
        self.build = self.makeBuild()

    def test_getUploadLogContent_nolog(self):
        """If there is no log file there, a string explanation is returned.
        """
        self.useTempDir()
        self.assertEquals('Could not find upload log file',
            self.build.getUploadLogContent(os.getcwd(), "myleaf"))

    def test_getUploadLogContent_only_dir(self):
        """If there is a directory but no log file, expect the error string,
        not an exception."""
        self.useTempDir()
        os.makedirs("accepted/myleaf")
        self.assertEquals('Could not find upload log file',
            self.build.getUploadLogContent(os.getcwd(), "myleaf"))

    def test_getUploadLogContent_readsfile(self):
        """If there is a log file, return its contents."""
        self.useTempDir()
        os.makedirs("accepted/myleaf")
        with open('accepted/myleaf/uploader.log', 'w') as f:
            f.write('foo')
        self.assertEquals('foo',
            self.build.getUploadLogContent(os.getcwd(), "myleaf"))

    def test_getUploaderCommand(self):
        upload_leaf = self.factory.getUniqueString('upload-leaf')
        config_args = list(config.builddmaster.uploader.split())
        log_file = self.factory.getUniqueString('logfile')
        config_args.extend(
            ['--log-file', log_file,
             '-d', self.build.distribution.name,
             '-s', (self.build.distro_series.name
                    + pocketsuffix[self.build.pocket]),
             '-b', str(self.build.id),
             '-J', upload_leaf,
             '--context=%s' % self.build.policy_name,
             os.path.abspath(config.builddmaster.root),
             ])
        uploader_command = self.build.getUploaderCommand(
            self.build, upload_leaf, log_file)
        self.assertEqual(config_args, uploader_command)


class TestHandleStatusMixin:
    """Tests for `IPackageBuild`s handleStatus method.

    Note: these tests do *not* test the updating of the build
    status to FULLYBUILT as this happens during the upload which
    is stubbed out by a mock function.
    """

    layer = LaunchpadZopelessLayer

    def makeBuild(self):
        """Allow classes to override the build with which the test runs."""
        raise NotImplementedError

    def setUp(self):
        super(TestHandleStatusMixin, self).setUp()
        self.build = self.makeBuild()
        # For the moment, we require a builder for the build so that
        # handleStatus_OK can get a reference to the slave.
        builder = self.factory.makeBuilder()
        self.build.buildqueue_record.builder = builder
        self.build.buildqueue_record.setDateStarted(UTC_NOW)
        self.slave = WaitingSlave('BuildStatus.OK')
        self.slave.valid_file_hashes.append('test_file_hash')
        builder.setSlaveForTesting(self.slave)

        # We overwrite the buildmaster root to use a temp directory.
        tmp_dir = self.makeTemporaryDirectory()
        tmp_builddmaster_root = """
        [builddmaster]
        root: %s
        """ % tmp_dir
        config.push('tmp_builddmaster_root', tmp_builddmaster_root)

        # We stub out our builds getUploaderCommand() method so
        # we can check whether it was called as well as
        # verifySuccessfulUpload().
        self.fake_getUploaderCommand = FakeMethod(
            result=['echo', 'noop'])
        removeSecurityProxy(self.build).getUploaderCommand = (
            self.fake_getUploaderCommand)
        removeSecurityProxy(self.build).verifySuccessfulUpload = FakeMethod(
            result=True)

    def test_handleStatus_OK_normal_file(self):
        # A filemap with plain filenames should not cause a problem.
        # The call to handleStatus will attempt to get the file from
        # the slave resulting in a URL error in this test case.
        self.build.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })

        self.assertEqual(BuildStatus.FULLYBUILT, self.build.status)
        self.assertEqual(1, self.fake_getUploaderCommand.call_count)

    def test_handleStatus_OK_absolute_filepath(self):
        # A filemap that tries to write to files outside of
        # the upload directory will result in a failed upload.
        self.build.handleStatus('OK', None, {
            'filemap': {'/tmp/myfile.py': 'test_file_hash'},
            })
        self.assertEqual(BuildStatus.FAILEDTOUPLOAD, self.build.status)
        self.assertEqual(0, self.fake_getUploaderCommand.call_count)

    def test_handleStatus_OK_relative_filepath(self):
        # A filemap that tries to write to files outside of
        # the upload directory will result in a failed upload.
        self.build.handleStatus('OK', None, {
            'filemap': {'../myfile.py': 'test_file_hash'},
            })
        self.assertEqual(BuildStatus.FAILEDTOUPLOAD, self.build.status)
        self.assertEqual(0, self.fake_getUploaderCommand.call_count)

    def test_handleStatus_OK_sets_build_log(self):
        # The build log is set during handleStatus.
        removeSecurityProxy(self.build).log = None
        self.assertEqual(None, self.build.log)
        self.build.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })
        self.assertNotEqual(None, self.build.log)

    def test_date_finished_set(self):
        # The date finished is updated during handleStatus_OK.
        removeSecurityProxy(self.build).date_finished = None
        self.assertEqual(None, self.build.date_finished)
        self.build.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })
        self.assertNotEqual(None, self.build.date_finished)
