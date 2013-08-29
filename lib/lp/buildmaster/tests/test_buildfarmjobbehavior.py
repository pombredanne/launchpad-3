# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for BuildFarmJobBehaviorBase."""

__metaclass__ = type

from datetime import datetime
import os
import shutil
import tempfile

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.archiveuploader.uploadprocessor import parse_build_upload_leaf_name
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interactor import BuilderInteractor
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.buildmaster.model.buildfarmjobbehavior import BuildFarmJobBehaviorBase
from lp.buildmaster.tests.mock_slaves import WaitingSlave
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.soyuz.interfaces.processor import IProcessorFamilySet
from lp.testing import TestCaseWithFactory
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.fakemethod import FakeMethod
from lp.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.mail_helpers import pop_notifications


class FakeBuildFarmJob:
    """Dummy BuildFarmJob."""
    pass


class TestBuildFarmJobBehaviorBase(TestCaseWithFactory):
    """Test very small, basic bits of BuildFarmJobBehaviorBase."""

    layer = ZopelessDatabaseLayer

    def _makeBehavior(self, buildfarmjob=None):
        """Create a `BuildFarmJobBehaviorBase`."""
        if buildfarmjob is None:
            buildfarmjob = FakeBuildFarmJob()
        else:
            buildfarmjob = removeSecurityProxy(buildfarmjob)
        return BuildFarmJobBehaviorBase(buildfarmjob)

    def _makeBuild(self):
        """Create a `Build` object."""
        x86 = getUtility(IProcessorFamilySet).getByName('x86')
        distroarchseries = self.factory.makeDistroArchSeries(
            architecturetag='x86', processorfamily=x86)
        distroseries = distroarchseries.distroseries
        archive = self.factory.makeArchive(
            distribution=distroseries.distribution)
        pocket = PackagePublishingPocket.RELEASE
        spr = self.factory.makeSourcePackageRelease(
            distroseries=distroseries, archive=archive)

        return spr.createBuild(
            distroarchseries=distroarchseries, pocket=pocket, archive=archive)

    def _makeBuildQueue(self):
        """Create a `BuildQueue` object."""
        return self.factory.makeSourcePackageRecipeBuildJob()

    def _changeBuildFarmJobName(self, buildfarmjob):
        """Manipulate `buildfarmjob` so that its `getName` changes."""
        name = buildfarmjob.getName() + 'x'
        removeSecurityProxy(buildfarmjob).getName = FakeMethod(result=name)

    def test_cookie_baseline(self):
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()

        cookie = buildfarmjob.generateSlaveBuildCookie()

        self.assertNotEqual(None, cookie)
        self.assertNotEqual(0, len(cookie))
        self.assertTrue(len(cookie) > 10)

        self.assertEqual(cookie, buildfarmjob.generateSlaveBuildCookie())

    def test_cookie_includes_job_name(self):
        # The cookie is a hash that includes the job's name.
        buildfarmjob = self.factory.makeTranslationTemplatesBuildJob()
        cookie = buildfarmjob.generateSlaveBuildCookie()
        self._changeBuildFarmJobName(removeSecurityProxy(buildfarmjob))

        self.assertNotEqual(cookie, buildfarmjob.generateSlaveBuildCookie())
        self.assertNotIn(buildfarmjob.getName(), cookie)

    def test_cookie_includes_more_than_name(self):
        # Two build jobs with the same name still get different cookies.
        buildfarmjob1 = self.factory.makeTranslationTemplatesBuildJob()
        buildfarmjob1 = removeSecurityProxy(buildfarmjob1)
        buildfarmjob2 = self.factory.makeTranslationTemplatesBuildJob(
            branch=buildfarmjob1.branch)
        buildfarmjob2 = removeSecurityProxy(buildfarmjob2)

        name_factory = FakeMethod(result="same-name")
        buildfarmjob1.getName = name_factory
        buildfarmjob2.getName = name_factory

        self.assertEqual(buildfarmjob1.getName(), buildfarmjob2.getName())
        self.assertNotEqual(
            buildfarmjob1.generateSlaveBuildCookie(),
            buildfarmjob2.generateSlaveBuildCookie())

    def test_getUploadDirLeaf(self):
        # getUploadDirLeaf returns the current time, followed by the build
        # cookie.
        now = datetime.now()
        build_cookie = self.factory.getUniqueString()
        upload_leaf = self._makeBehavior().getUploadDirLeaf(
            build_cookie, now=now)
        self.assertEqual(
            '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_cookie),
            upload_leaf)


class TestGetUploadMethodsMixin:
    """Tests for `IPackageBuild` that need objects from the rest of LP."""

    layer = LaunchpadZopelessLayer

    def makeBuild(self):
        """Allow classes to override the build with which the test runs."""
        raise NotImplemented

    def setUp(self):
        super(TestGetUploadMethodsMixin, self).setUp()
        self.build = self.makeBuild()
        self.behavior = IBuildFarmJobBehavior(
            self.build.buildqueue_record.specific_job)

    def test_getUploadDirLeafCookie_parseable(self):
        # getUploadDirLeaf should return a directory name
        # that is parseable by the upload processor.
        upload_leaf = self.behavior.getUploadDirLeaf(
            self.behavior.getBuildCookie())
        (job_type, job_id) = parse_build_upload_leaf_name(upload_leaf)
        self.assertEqual(
            (self.build.job_type.name, self.build.id), (job_type, job_id))


class TestHandleStatusMixin:
    """Tests for `IPackageBuild`s handleStatus method.

    This should be run with a Trial TestCase.
    """

    layer = LaunchpadZopelessLayer

    def makeBuild(self):
        """Allow classes to override the build with which the test runs."""
        raise NotImplementedError

    def setUp(self):
        super(TestHandleStatusMixin, self).setUp()
        self.factory = LaunchpadObjectFactory()
        self.build = self.makeBuild()
        # For the moment, we require a builder for the build so that
        # handleStatus_OK can get a reference to the slave.
        self.builder = self.factory.makeBuilder()
        self.build.buildqueue_record.builder = self.builder
        self.build.buildqueue_record.setDateStarted(UTC_NOW)
        self.slave = WaitingSlave('BuildStatus.OK')
        self.slave.valid_file_hashes.append('test_file_hash')
        self.interactor = BuilderInteractor(self.builder, self.slave)
        self.behavior = removeSecurityProxy(
            self.interactor._current_build_behavior)

        # We overwrite the buildmaster root to use a temp directory.
        tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tempdir)
        self.upload_root = tempdir
        tmp_builddmaster_root = """
        [builddmaster]
        root: %s
        """ % self.upload_root
        config.push('tmp_builddmaster_root', tmp_builddmaster_root)

        # We stub out our builds getUploaderCommand() method so
        # we can check whether it was called as well as
        # verifySuccessfulUpload().
        removeSecurityProxy(self.build).verifySuccessfulUpload = FakeMethod(
            result=True)

    def assertResultCount(self, count, result):
        self.assertEquals(
            1, len(os.listdir(os.path.join(self.upload_root, result))))

    def test_handleStatus_OK_normal_file(self):
        # A filemap with plain filenames should not cause a problem.
        # The call to handleStatus will attempt to get the file from
        # the slave resulting in a URL error in this test case.
        def got_status(ignored):
            self.assertEqual(BuildStatus.UPLOADING, self.build.status)
            self.assertResultCount(1, "incoming")

        d = self.behavior.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })
        return d.addCallback(got_status)

    def test_handleStatus_OK_absolute_filepath(self):
        # A filemap that tries to write to files outside of
        # the upload directory will result in a failed upload.
        def got_status(ignored):
            self.assertEqual(BuildStatus.FAILEDTOUPLOAD, self.build.status)
            self.assertResultCount(0, "failed")
            self.assertIdentical(None, self.build.buildqueue_record)

        d = self.behavior.handleStatus('OK', None, {
            'filemap': {'/tmp/myfile.py': 'test_file_hash'},
            })
        return d.addCallback(got_status)

    def test_handleStatus_OK_relative_filepath(self):
        # A filemap that tries to write to files outside of
        # the upload directory will result in a failed upload.
        def got_status(ignored):
            self.assertEqual(BuildStatus.FAILEDTOUPLOAD, self.build.status)
            self.assertResultCount(0, "failed")

        d = self.behavior.handleStatus('OK', None, {
            'filemap': {'../myfile.py': 'test_file_hash'},
            })
        return d.addCallback(got_status)

    def test_handleStatus_OK_sets_build_log(self):
        # The build log is set during handleStatus.
        self.assertEqual(None, self.build.log)
        d = self.behavior.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })

        def got_status(ignored):
            self.assertNotEqual(None, self.build.log)

        return d.addCallback(got_status)

    def _test_handleStatus_notifies(self, status):
        # An email notification is sent for a given build status if
        # notifications are allowed for that status.

        expected_notification = (
            status in self.behavior.ALLOWED_STATUS_NOTIFICATIONS)

        def got_status(ignored):
            if expected_notification:
                self.failIf(
                    len(pop_notifications()) == 0,
                    "No notifications received")
            else:
                self.failIf(
                    len(pop_notifications()) > 0,
                    "Notifications received")

        d = self.behavior.handleStatus(status, None, {})
        return d.addCallback(got_status)

    def test_handleStatus_DEPFAIL_notifies(self):
        return self._test_handleStatus_notifies("DEPFAIL")

    def test_handleStatus_CHROOTFAIL_notifies(self):
        return self._test_handleStatus_notifies("CHROOTFAIL")

    def test_handleStatus_PACKAGEFAIL_notifies(self):
        return self._test_handleStatus_notifies("PACKAGEFAIL")

    def test_handleStatus_ABORTED_cancels_cancelling(self):
        self.build.updateStatus(BuildStatus.CANCELLING)

        def got_status(ignored):
            self.assertEqual(
                0, len(pop_notifications()), "Notifications received")
            self.assertEqual(BuildStatus.CANCELLED, self.build.status)

        d = self.behavior.handleStatus("ABORTED", None, {})
        return d.addCallback(got_status)

    def test_handleStatus_ABORTED_recovers_building(self):
        self.builder.vm_host = "fake_vm_host"
        self.build.updateStatus(BuildStatus.BUILDING)

        def got_status(ignored):
            self.assertEqual(
                0, len(pop_notifications()), "Notifications received")
            self.assertEqual(BuildStatus.NEEDSBUILD, self.build.status)
            self.assertEqual(1, self.builder.failure_count)
            self.assertIn("resume", self.slave.call_log)

        d = self.behavior.handleStatus("ABORTED", None, {})
        return d.addCallback(got_status)

    def test_date_finished_set(self):
        # The date finished is updated during handleStatus_OK.
        self.assertEqual(None, self.build.date_finished)
        d = self.behavior.handleStatus('OK', None, {
                'filemap': {'myfile.py': 'test_file_hash'},
                })

        def got_status(ignored):
            self.assertNotEqual(None, self.build.date_finished)

        return d.addCallback(got_status)
