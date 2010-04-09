# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TranslationTemplatesBuildBehavior."""

import logging
import os
from StringIO import StringIO
import transaction
from unittest import TestLoader

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior)
from lp.buildmaster.interfaces.builder import CorruptBuildID
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue)
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode)


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
        self._status = {
            'test_build_started': False,
        }

        self.cacheFile = FakeMethod()
        self.getFile = FakeMethod(result=StringIO("File from the slave."))

    def build(self, buildid, build_type, chroot_sha1, filemap, args):
        """Pretend to start a build."""
        self._status['build_id'] = buildid
        self._status['filemap'] = filemap

        # Chuck in some information that a real slave wouldn't store,
        # but which will allow tests to check up on the build call.
        self._status['test_build_type'] = build_type
        self._status['test_build_args'] = args
        self._status['test_build_started'] = True

    def status(self):
        return (
            'BuilderStatus.WAITING',
            'BuildStatus.OK',
            self._status.get('build_id'),
            self._status.get('filemap'),
            )


class FakeBuilder:
    """Pretend `Builder`."""
    def __init__(self, slave):
        self.slave = slave
        self.cleanSlave = FakeMethod()

    def slaveStatus(self):
        return self.slave._status


class FakeBuildQueue:
    """Pretend `BuildQueue`."""
    def __init__(self, behavior):
        """Pretend to be a BuildQueue item for the given build behavior.

        Copies its builder from the behavior object.
        """
        self.builder = behavior._builder
        self.specific_job = behavior.buildfarmjob
        self.destroySelf = FakeMethod()


class MakeBehaviorMixin(object):
    """Provide common test methods."""

    def makeBehavior(self, branch=None):
        """Create a TranslationTemplatesBuildBehavior.

        Anything that might communicate with build slaves and such
        (which we can't really do here) is mocked up.
        """
        specific_job = self.factory.makeTranslationTemplatesBuildJob(
            branch=branch)
        behavior = IBuildFarmJobBehavior(specific_job)
        slave = FakeSlave(BuildStatus.NEEDSBUILD)
        behavior._builder = FakeBuilder(slave)
        return behavior


class TestTranslationTemplatesBuildBehavior(
        TestCaseWithFactory, MakeBehaviorMixin):
    """Test `TranslationTemplatesBuildBehavior`."""

    layer = LaunchpadZopelessLayer

    def _becomeBuilddMaster(self):
        """Log into the database as the buildd master."""
        transaction.commit()
        self.layer.switchDbUser(config.builddmaster.dbuser)

    def _getBuildQueueItem(self, behavior):
        """Get `BuildQueue` for an `IBuildFarmJobBehavior`."""
        job = removeSecurityProxy(behavior.buildfarmjob.job)
        return getUtility(IBuildQueueSet).getByJob(job.id)

    def test_dispatchBuildToSlave(self):
        # dispatchBuildToSlave ultimately causes the slave's build
        # method to be invoked.  The slave receives the URL of the
        # branch it should build from.
        behavior = self.makeBehavior()
        behavior._getChroot = FakeChroot
        buildqueue_item = self._getBuildQueueItem(behavior)

        self._becomeBuilddMaster()
        behavior.dispatchBuildToSlave(buildqueue_item, logging)

        slave_status = behavior._builder.slaveStatus()
        self.assertTrue(slave_status['test_build_started'])
        self.assertEqual(
            'translation-templates', slave_status['test_build_type'])
        self.assertIn('branch_url', slave_status['test_build_args'])
        # The slave receives the public http URL for the branch.
        self.assertEqual(
            behavior.buildfarmjob.branch.composePublicURL(),
            slave_status['test_build_args']['branch_url'])

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

        behavior = self.makeBehavior()
        chroot = behavior._getChroot()

        self.assertNotEqual(None, chroot)
        self.assertEqual(fake_chroot_file, chroot)

    def test_readTarball(self):
        behavior = self.makeBehavior()
        buildqueue = FakeBuildQueue(behavior)
        path = behavior.templates_tarball_path
        self.assertEqual(
            "File from the slave.",
            behavior._readTarball(buildqueue, {path: path}, logging))

    def test_updateBuild_WAITING(self):
        behavior = self.makeBehavior()
        behavior._getChroot = FakeChroot
        behavior._uploadTarball = FakeMethod()
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder

        behavior.dispatchBuildToSlave(queue_item, logging)

        self.assertEqual(0, queue_item.destroySelf.call_count)
        self.assertEqual(0, builder.cleanSlave.call_count)
        self.assertEqual(0, behavior._uploadTarball.call_count)

        slave_status = {
            'builder_status': builder.slave.status()[0],
            'build_status': builder.slave.status()[1],
            }
        behavior.updateSlaveStatus(builder.slave.status(), slave_status)
        behavior.updateBuild_WAITING(queue_item, slave_status, None, logging)

        self.assertEqual(1, queue_item.destroySelf.call_count)
        self.assertEqual(1, builder.cleanSlave.call_count)
        self.assertEqual(0, behavior._uploadTarball.call_count)

    def test_verifySlaveBuildID_success(self):
        # TranslationTemplatesBuildJob.getName generates slave build ids
        # that TranslationTemplatesBuildBehavior.verifySlaveBuildID
        # accepts.
        behavior = self.makeBehavior()
        buildfarmjob = behavior.buildfarmjob
        job = buildfarmjob.job

        # The test is that this not raise CorruptBuildID (or anything
        # else, for that matter).
        behavior.verifySlaveBuildID(behavior.buildfarmjob.getName())

    def test_verifySlaveBuildID_handles_dashes(self):
        # TranslationTemplatesBuildBehavior.verifySlaveBuildID can deal
        # with dashes in branch names.
        behavior = self.makeBehavior()
        buildfarmjob = behavior.buildfarmjob
        job = buildfarmjob.job
        buildfarmjob.branch.name = 'x-y-z--'

        # The test is that this not raise CorruptBuildID (or anything
        # else, for that matter).
        behavior.verifySlaveBuildID(behavior.buildfarmjob.getName())

    def test_verifySlaveBuildID_malformed(self):
        behavior = self.makeBehavior()
        self.assertRaises(CorruptBuildID, behavior.verifySlaveBuildID, 'huh?')

    def test_verifySlaveBuildID_notfound(self):
        behavior = self.makeBehavior()
        self.assertRaises(CorruptBuildID, behavior.verifySlaveBuildID, '1-1')


class TestTTBuildBehaviorTranslationsQueue(
        TestCaseWithFactory, MakeBehaviorMixin):
    """Test uploads to the import queue."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestTTBuildBehaviorTranslationsQueue, self).setUp()

        self.queue = getUtility(ITranslationImportQueue)
        self.productseries = self.factory.makeProductSeries()
        self.branch = self.factory.makeProductBranch(
            self.productseries.product)
        self.productseries.branch = self.branch
        self.productseries.translations_autoimport_mode = (
            TranslationsBranchImportMode.IMPORT_TEMPLATES)
        self.dummy_tar = os.path.join(
            os.path.dirname(__file__),'dummy_templates.tar.gz')

    def _getPaths(self, entries):
        return [entry.path for entry in entries]

    def test_uploadTarball(self):
        # Files from the tarball end up in the import queue.
        behavior = self.makeBehavior()
        behavior._uploadTarball(
            self.branch, file(self.dummy_tar).read(), None)

        entries = self.queue.getAllEntries(target=self.productseries)
        expected_templates = [
            'po/messages.pot',
            'po-other/other.pot',
            'po-thethird/templ3.pot'
            ]
        self.assertContentEqual(expected_templates, self._getPaths(entries))

    def test_uploadTarball_importer(self):
        # Files from the tarball are owned by the branch owner.
        behavior = self.makeBehavior()
        behavior._uploadTarball(
            self.branch, file(self.dummy_tar).read(), None)

        entries = self.queue.getAllEntries(target=self.productseries)
        self.assertEqual(self.branch.owner, entries[0].importer)

    def test_updateBuild_WAITING_uploads(self):
        behavior = self.makeBehavior(branch=self.branch)
        behavior._getChroot = FakeChroot
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder

        behavior.dispatchBuildToSlave(queue_item, logging)

        builder.slave.getFile.result = open(self.dummy_tar)
        builder.slave._status['filemap'] = {
            'translation-templates.tar.gz': 'foo'}
        slave_status = {
            'builder_status': builder.slave.status()[0],
            'build_status': builder.slave.status()[1],
            'build_id': builder.slave.status()[2]
            }
        behavior.updateSlaveStatus(builder.slave.status(), slave_status)
        behavior.updateBuild_WAITING(queue_item, slave_status, None, logging)

        entries = self.queue.getAllEntries(target=self.productseries)
        expected_templates = [
            'po/messages.pot',
            'po-other/other.pot',
            'po-thethird/templ3.pot'
            ]
        self.assertContentEqual(expected_templates, self._getPaths(entries))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

