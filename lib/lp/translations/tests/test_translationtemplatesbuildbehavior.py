# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TranslationTemplatesBuildBehavior."""

import logging
from StringIO import StringIO
from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import ZopelessDatabaseLayer

from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class FakeChrootContent:
    """Pretend chroot contents."""
    sha1 = "shasha"


class FakeChroot:
    """Pretend chroot."""
    def __init__(self, *args, **kwargs):
        """Constructor acts as a fake _getChroot."""
        self.content = FakeChrootContent()


class FakeSlave:
    """Pretend build slave."""
    def __init__(self, builderstatus):
        self.status = {
            'build_status': 'BuildStatus.%s' % builderstatus.name,
            'test_build_started': False,
        }

        self.cacheFile = FakeMethod()
        self.getFile = FakeMethod(result=StringIO("File from the slave."))

    def build(self, buildid, build_type, chroot_sha1, filemap, args):
        """Pretend to start a build."""
        self.status['build_id'] = buildid
        self.status['filemap'] = filemap

        # Chuck in some information that a real slave wouldn't store,
        # but which will allow tests to check up on the build call.
        self.status['test_build_type'] = build_type
        self.status['test_build_args'] = args
        self.status['test_build_started'] = True


class FakeBuilder:
    """Pretend `Builder`."""
    def __init__(self, slave):
        self.slave = slave
        self.cleanSlave = FakeMethod()

    def slaveStatus(self):
        return self.slave.status


class FakeBuildQueue:
    """Pretend `BuildQueue`."""
    def __init__(self, behavior):
        """Pretend to be a BuildQueue item for the given build behavior.

        Copies its builder from the behavior object.
        """
        self.builder = behavior._builder
        self.destroySelf = FakeMethod()


class TestTranslationTemplatesBuildBehavior(TestCaseWithFactory):
    """Test `TranslationTemplatesBuildBehavior`."""

    layer = ZopelessDatabaseLayer

    def _makeBehavior(self):
        """Create a TranslationTemplatesBuildBehavior.

        Anything that might communicate with build slaves and such
        (which we can't really do here) is mocked up.
        """
        specific_job = self.factory.makeTranslationTemplatesBuildJob()
        behavior = IBuildFarmJobBehavior(specific_job)
        slave = FakeSlave(BuildStatus.NEEDSBUILD)
        behavior._builder = FakeBuilder(slave)
        return behavior

    def _getBuildQueueItem(self, behavior):
        """Get `BuildQueue` for an `IBuildFarmJobBehavior`."""
        job = removeSecurityProxy(behavior.buildfarmjob.job)
        return getUtility(IBuildQueueSet).getByJob(job.id)

    def test_dispatchBuildToSlave(self):
        # dispatchBuildToSlave ultimately causes the slave's build
        # method to be invoked.  The slave receives the URL of the
        # branch it should build from.
        behavior = self._makeBehavior()
        behavior._getChroot = FakeChroot
        buildqueue_item = self._getBuildQueueItem(behavior)

        behavior.dispatchBuildToSlave(buildqueue_item, logging)

        slave_status = behavior._builder.slaveStatus()
        self.assertTrue(slave_status['test_build_started'])
        self.assertEqual(
            'translation-templates', slave_status['test_build_type'])
        self.assertIn('branch_url', slave_status['test_build_args'])

    def test_getChroot(self):
        # _getChroot produces the current chroot for the current Ubuntu
        # release, on the nominated architecture for
        # architecture-independent builds.
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        current_ubuntu = ubuntu.currentseries
        distroarchseries = current_ubuntu.nominatedarchindep

        # Set an arbitrary chroot file.
        fake_chroot_file = getUtility(ILibraryFileAliasSet)[1]
        distroarchseries.addOrUpdateChroot(fake_chroot_file)

        behavior = self._makeBehavior()
        chroot = behavior._getChroot()

        self.assertNotEqual(None, chroot)
        self.assertEqual(fake_chroot_file, chroot)

    def test_readTarball(self):
        behavior = self._makeBehavior()
        buildqueue = FakeBuildQueue(behavior)
        path = behavior.templates_tarball_path
        self.assertEqual(
            "File from the slave.",
            behavior._readTarball(buildqueue, {path: path}, logging))

    def test_updateBuild_WAITING(self):
        behavior = self._makeBehavior()
        behavior._getChroot = FakeChroot
        behavior._uploadTarball = FakeMethod()
        queue_item = FakeBuildQueue(behavior)
        slave_status = behavior._builder.slave.status
        builder = behavior._builder

        behavior.dispatchBuildToSlave(queue_item, logging)

        self.assertEqual(0, queue_item.destroySelf.call_count)
        self.assertEqual(0, builder.cleanSlave.call_count)
        self.assertEqual(0, behavior._uploadTarball.call_count)

        behavior.updateBuild_WAITING(queue_item, slave_status, None, logging)

        self.assertEqual(1, queue_item.destroySelf.call_count)
        self.assertEqual(1, builder.cleanSlave.call_count)
        self.assertEqual(0, behavior._uploadTarball.call_count)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

