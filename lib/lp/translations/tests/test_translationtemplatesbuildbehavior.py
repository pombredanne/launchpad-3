# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TranslationTemplatesBuildBehavior."""

import logging
import os
from StringIO import StringIO
from unittest import TestLoader

import transaction
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.testing import LaunchpadZopelessLayer
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.tests.mock_slaves import WaitingSlave
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    IBuildFarmJobBehavior,
    )
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue,
    RosettaImportStatus,
    )
from lp.translations.interfaces.translations import (
    TranslationsBranchImportMode,
    )


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

    def makeBehavior(self, branch=None, use_fake_chroot=True):
        """Create a TranslationTemplatesBuildBehavior.

        Anything that might communicate with build slaves and such
        (which we can't really do here) is mocked up.
        """
        specific_job = self.factory.makeTranslationTemplatesBuildJob(
            branch=branch)
        behavior = IBuildFarmJobBehavior(specific_job)
        # XXX
        #slave = FakeSlave(BuildStatus.NEEDSBUILD)
        slave = WaitingSlave()
        #behavior._builder = FakeBuilder(slave)
        behavior._builder = removeSecurityProxy(self.factory.makeBuilder())
        behavior._builder.setSlaveForTesting(slave)
        if use_fake_chroot:
            lf = self.factory.makeLibraryFileAlias()
            self.layer.txn.commit()
            behavior._getChroot = lambda: lf
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
        buildqueue_item = self._getBuildQueueItem(behavior)

        self._becomeBuilddMaster()
        behavior.dispatchBuildToSlave(buildqueue_item, logging)

        # call_log lives on the mock WaitingSlave and tells us what
        # calls to the slave that the behaviour class made.
        call_log = behavior._builder.slave.call_log
        build_params = call_log[-1]
        self.assertEqual('build', build_params[0])
        build_type = build_params[2]
        self.assertEqual('translation-templates', build_type)
        branch_url = build_params[-1]['branch_url']
        # The slave receives the public http URL for the branch.
        self.assertEqual(
            branch_url, 
            behavior.buildfarmjob.branch.composePublicURL())



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

        behavior = self.makeBehavior(use_fake_chroot=False)
        chroot = behavior._getChroot()

        self.assertNotEqual(None, chroot)
        self.assertEqual(fake_chroot_file, chroot)

    def test_readTarball(self):
        behavior = self.makeBehavior()
        buildqueue = FakeBuildQueue(behavior)
        path = behavior.templates_tarball_path
        # Poke the file we're expecting into the mock slave.
        behavior._builder.slave.valid_file_hashes.append(path)
        self.assertEqual(
            "This is a %s" % path,
            behavior._readTarball(buildqueue, {path: path}, logging))

    def test_updateBuild_WAITING_OK(self):
        # Hopefully, a build will succeed and produce a tarball.
        behavior = self.makeBehavior()
        behavior._uploadTarball = FakeMethod()
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder

        behavior.dispatchBuildToSlave(queue_item, logging)

        self.assertEqual(0, queue_item.destroySelf.call_count)
        slave_call_log = behavior._builder.slave.call_log
        self.assertNotIn('clean', slave_call_log)
        self.assertEqual(0, behavior._uploadTarball.call_count)

        slave_status = {
            'builder_status': builder.slave.status()[0],
            'build_status': builder.slave.status()[1],
            }
        behavior.updateSlaveStatus(builder.slave.status(), slave_status)
        behavior.updateBuild_WAITING(queue_item, slave_status, None, logging)

        self.assertEqual(1, queue_item.destroySelf.call_count)
        self.assertIn('clean', slave_call_log)
        self.assertEqual(0, behavior._uploadTarball.call_count)

    def test_updateBuild_WAITING_failed(self):
        # Builds may also fail (and produce no tarball).
        behavior = self.makeBehavior()
        behavior._uploadTarball = FakeMethod()
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder
        behavior.dispatchBuildToSlave(queue_item, logging)
        raw_status = (
            'BuilderStatus.WAITING',
            'BuildStatus.FAILEDTOBUILD',
            builder.slave.status()[2],
            )
        status_dict = {
            'builder_status': raw_status[0],
            'build_status': raw_status[1],
            }
        behavior.updateSlaveStatus(raw_status, status_dict)
        self.assertNotIn('filemap', status_dict)

        behavior.updateBuild_WAITING(queue_item, status_dict, None, logging)

        self.assertEqual(1, queue_item.destroySelf.call_count)
        slave_call_log = behavior._builder.slave.call_log
        self.assertIn('clean', slave_call_log)
        self.assertEqual(0, behavior._uploadTarball.call_count)

    def test_updateBuild_WAITING_notarball(self):
        # Even if the build status is "OK," absence of a tarball will
        # not faze the Behavior class.
        behavior = self.makeBehavior()
        behavior._uploadTarball = FakeMethod()
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder
        behavior.dispatchBuildToSlave(queue_item, logging)
        raw_status = (
            'BuilderStatus.WAITING',
            'BuildStatus.OK',
            builder.slave.status()[2],
            )
        status_dict = {
            'builder_status': raw_status[0],
            'build_status': raw_status[1],
            }
        behavior.updateSlaveStatus(raw_status, status_dict)
        self.assertFalse('filemap' in status_dict)

        behavior.updateBuild_WAITING(queue_item, status_dict, None, logging)

        self.assertEqual(1, queue_item.destroySelf.call_count)
        slave_call_log = behavior._builder.slave.call_log
        self.assertIn('clean', slave_call_log)
        self.assertEqual(0, behavior._uploadTarball.call_count)


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

    def test_uploadTarball(self):
        # Files from the tarball end up in the import queue.
        behavior = self.makeBehavior()
        behavior._uploadTarball(
            self.branch, file(self.dummy_tar).read(), None)

        entries = self.queue.getAllEntries(target=self.productseries)
        expected_templates = [
            'po/domain.pot',
            'po-other/other.pot',
            'po-thethird/templ3.pot'
            ]

        paths = [entry.path for entry in entries]
        self.assertContentEqual(expected_templates, paths)

    def test_uploadTarball_approved(self):
        # Uploaded template files are automatically approved.
        behavior = self.makeBehavior()
        behavior._uploadTarball(
            self.branch, file(self.dummy_tar).read(), None)

        entries = self.queue.getAllEntries(target=self.productseries)
        statuses = [entry.status for entry in entries]
        self.assertEqual(
            [RosettaImportStatus.APPROVED] * 3, statuses)

    def test_uploadTarball_importer(self):
        # Files from the tarball are owned by the branch owner.
        behavior = self.makeBehavior()
        behavior._uploadTarball(
            self.branch, file(self.dummy_tar).read(), None)

        entries = self.queue.getAllEntries(target=self.productseries)
        self.assertEqual(self.branch.owner, entries[0].importer)

    def test_updateBuild_WAITING_uploads(self):
        behavior = self.makeBehavior(branch=self.branch)
        queue_item = FakeBuildQueue(behavior)
        builder = behavior._builder

        behavior.dispatchBuildToSlave(queue_item, logging)

        builder.slave.getFile = lambda sum: open(self.dummy_tar)
        builder.slave.filemap = {
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
            'po/domain.pot',
            'po-other/other.pot',
            'po-thethird/templ3.pot'
            ]
        self.assertContentEqual(
            expected_templates, [entry.path for entry in entries])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

