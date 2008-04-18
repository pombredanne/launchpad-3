# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test buildd uploads use-cases."""

__metaclass__ = type

import unittest

from canonical.archiveuploader.ftests.test_securityuploads import (
    TestStagedBinaryUploadBase)
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.database.constants import UTC_NOW
from canonical.launchpad.interfaces import (
    PackagePublishingPocket, PackagePublishingStatus)
from canonical.launchpad.ftests import import_public_test_keys

class TestBuilddUploads(TestStagedBinaryUploadBase):
    """Test how buildd uploads behave inside Soyuz.

    Buildd uploads are exclusively binary uploads which use 'buildd' upload
    policy.

    An upload of a binaries does not necessary need to happen in the same
    batch, and Soyuz is prepared to cope with it.

    The only mandatory condition is to process the sources first.

    This class will start to tests all known/possible cases using a test
    (empty) upload and its binary.

     * 'lib/canonical/archiveuploader/tests/data/suite/foo_1.0-1/'
     * 'lib/canonical/archiveuploader/tests/data/suite/foo_1.0-1_binary/'

    This class allows uploads to ubuntu/breezy in i386 & powerpc architectures.
    """
    name = 'foo'
    version = '1.0-1'
    distribution_name = 'ubuntu'
    distroseries_name = 'breezy'
    pocket = PackagePublishingPocket.RELEASE
    policy = 'buildd'
    no_mails = True

    def setupBreezy(self):
        """Extend breezy setup to enable uploads to powerpc architecture."""
        TestStagedBinaryUploadBase.setupBreezy(self)
        from canonical.launchpad.database.processor import (
            Processor, ProcessorFamily)
        ppc_family = ProcessorFamily.selectOneBy(name='powerpc')
        ppc_proc = Processor(
            name='powerpc', title='PowerPC', description='not yet',
            family=ppc_family)
        breezy_ppc = self.breezy.newArch(
            'powerpc', ppc_proc, True, self.breezy.owner)

    def setUp(self):
        """Setup environment for binary uploads.

        1. import pub GPG keys
        2. setup ubuntu/breezy for i386 & powerpc
        3. override policy to upload the source in question via
           TestStagedBinaryUploadBase.setUp()
        4. restore 'buildd' policy.
        """
        import_public_test_keys()
        self.setupBreezy()
        self.layer.txn.commit()

        real_policy = self.policy
        self.policy = 'insecure'
        TestStagedBinaryUploadBase.setUp(self)
        self.policy = real_policy

    def _publishBuildQueueItem(self, queue_item):
        """Publish build part of the given queue item."""
        queue_item.setAccepted()
        pubrec = queue_item.builds[0].publish(self.log)[0]
        pubrec.secure_record.status = PackagePublishingStatus.PUBLISHED
        pubrec.secure_record.datepublished = UTC_NOW
        queue_item.setDone()

    def _setupUploadProcessorForBuild(self, build_candidate):
        """Setup an UploadProcessor instance for a given buildd context."""
        self.options.context = self.policy
        self.options.buildid = str(build_candidate.id)
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

    def testDelayedBinaryUpload(self):
        """Check if Soyuz copes with delayed binary uploads.

        The binaries are build asynchronously, which means we can't
        predict if the builds for all architectures of a given source
        will be delivered within the same publication cycle.

        Find more information on bug #89846.
        """
        # Upload i386 binary.
        build_candidate = self._createBuild('i386')
        self._setupUploadProcessorForBuild(build_candidate)
        build_used = self._uploadBinary('i386')

        self.assertEqual(build_used.id, build_candidate.id)
        self.assertBuildsCreated(1)
        self.assertEqual(
            u'i386 build of foo 1.0-1 in ubuntu breezy RELEASE',
            build_used.title)
        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

        # Force immediate publication.
        queue_item = self.uploadprocessor.last_processed_upload.queue_root
        self._publishBuildQueueItem(queue_item)

        # Upload powerpc binary
        build_candidate = self._createBuild('powerpc')
        self._setupUploadProcessorForBuild(build_candidate)
        build_used = self._uploadBinary('powerpc')

        self.assertEqual(build_used.id, build_candidate.id)
        self.assertBuildsCreated(2)
        self.assertEqual(
            u'powerpc build of foo 1.0-1 in ubuntu breezy RELEASE',
            build_used.title)
        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

