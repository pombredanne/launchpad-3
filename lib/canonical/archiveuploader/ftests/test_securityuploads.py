# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Test security uploads use-cases."""

__metaclass__ = type

import os
import unittest

from zope.component import getUtility

from canonical.archiveuploader.ftests.test_uploadprocessor import (
    TestUploadProcessorBase)
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database.build import Build
from canonical.launchpad.database.processor import ProcessorFamily
from canonical.launchpad.interfaces import IDistributionSet
from canonical.lp.dbschema import (
    PackageUploadStatus, PackagePublishingStatus, PackagePublishingPocket)


class TestStagedBinaryUploadBase(TestUploadProcessorBase):
    name = 'baz'
    version = '1.0-1'
    distribution_name = None
    distroseries_name = None
    pocket = None
    policy = 'buildd'
    no_mails = True

    @property
    def distribution(self):
        return getUtility(IDistributionSet)[self.distribution_name]

    @property
    def distroseries(self):
        return self.distribution[self.distroseries_name]

    @property
    def package_name(self):
        return "%s_%s" % (self.name, self.version)

    @property
    def source_dir(self):
        return self.package_name

    @property
    def source_changesfile(self):
        return "%s_source.changes" % self.package_name

    @property
    def binary_dir(self):
        return "%s_binary" % self.package_name

    def getBinaryChangesfileFor(self, archtag):
        return "%s_%s.changes" % (self.package_name, archtag)

    def setUp(self):
        """Setup environment for staged binaries upload via security policy.

        1. Setup queue directory and other basic attributes
        2. Override policy options to get security policy and to not send emails
        3. Setup a common UploadProcessor with the overridden options
        4. Store number of build present before issuing any upload
        5. Upload the source package via security policy
        6. Clean log messages.
        7. Commit transaction, so the upload source can be seen.
        """
        TestUploadProcessorBase.setUp(self)
        self.options.context = self.policy
        self.options.nomails = self.no_mails
        # Set up the uploadprocessor with appropriate options and logger
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)
        self.builds_before_upload = Build.select().count()
        self.source_queue = None
        self._uploadSource()
        self.log.lines = []
        self.layer.txn.commit()

    def assertBuildsCreated(self, amount):
        """Assert that a given 'amount' of build records was created."""
        builds_count = Build.select().count()
        self.assertEqual(
            self.builds_before_upload + amount, builds_count)

    def _prepareUpload(self, upload_dir):
        """Place a copy of the upload directory into incoming queue."""
        os.system("cp -a %s %s" %
            (os.path.join(self.test_files_dir, upload_dir),
             os.path.join(self.queue_folder, "incoming")))

    def _uploadSource(self):
        """Upload and Accept (if necessary) the base source."""
        self._prepareUpload(self.source_dir)
        self.uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", self.source_dir),
            self.source_changesfile)
        queue_item = self.uploadprocessor.last_processed_upload.queue_root
        self.assertTrue(
            queue_item is not None,
            "Source Upload Failed\nGot: %s" % "\n".join(self.log.lines))
        acceptable_statuses = [
            PackageUploadStatus.NEW,
            PackageUploadStatus.UNAPPROVED,
            ]
        if queue_item.status in acceptable_statuses:
            queue_item.setAccepted()
        # Store source queue item for future use.
        self.source_queue = queue_item

    def _uploadBinary(self, archtag):
        """Upload the base binary.

        Ensure it got processed and has a respective queue record.
        Return the IBuild attached to upload.
        """
        self._prepareUpload(self.binary_dir)
        self.uploadprocessor.processChangesFile(
            os.path.join(self.queue_folder, "incoming", self.binary_dir),
            self.getBinaryChangesfileFor(archtag))
        queue_item = self.uploadprocessor.last_processed_upload.queue_root
        self.assertTrue(
            queue_item is not None,
            "Binary Upload Failed\nGot: %s" % "\n".join(self.log.lines))
        self.assertEqual(queue_item.builds.count(), 1)
        return queue_item.builds[0].build

    def _createBuild(self, archtag):
        """Create a build record attached to the base source."""
        spr = self.source_queue.sources[0].sourcepackagerelease
        build = spr.createBuild(
            distroarchseries=self.distroseries[archtag],
            pocket=self.pocket, archive=self.distroseries.main_archive)
        self.layer.txn.commit()
        return build


class TestStagedSecurityUploads(TestStagedBinaryUploadBase):
    """Test how security uploads behave inside Soyuz.

    Security uploads still coming from dak system, we have special upload
    policy which allows source and binary uploads.

    An upload of a source and its binaries does not necessary need
    to happen in the same batch, and Soyuz is prepared to cope with it.

    The only mandatory condition is to process the sources first.

    This class will start to tests all known/possible cases using a test
    (empty) upload and its binary.

     * 'lib/canonical/archivepublisher/tests/data/suite/baz_1.0-1/'
     * 'lib/canonical/archivepublisher/tests/data/suite/baz_1.0-1_binary/'
    """
    name = 'baz'
    version = '1.0-1'
    distribution_name = 'ubuntu'
    distroseries_name = 'warty'
    pocket = PackagePublishingPocket.SECURITY
    policy = 'security'
    no_mails = True

    def setUp(self):
        """Setup base class and create the required new distroarchseries."""
        TestStagedBinaryUploadBase.setUp(self)
        distribution = getUtility(IDistributionSet).getByName(
            self.distribution_name)
        distroseries = distribution[self.distroseries.name]
        proc_family = ProcessorFamily.selectOneBy(name='amd64')
        distroseries.newArch(
            'amd64', proc_family, True, distribution.owner)

    def testBuildCreation(self):
        """Check if the builds get created for a binary security uploads.

        That is the usual case, security binary uploads come after the
        not published (accepted) source but in the same batch.

        NascentUpload should create appropriate builds attached to the
        correct source for the incoming binaries.
        """
        build_used = self._uploadBinary('i386')

        self.assertBuildsCreated(1)
        self.assertEqual(
            u'i386 build of baz 1.0-1 in ubuntu warty SECURITY',
            build_used.title)
        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

        build_used = self._uploadBinary('amd64')

        self.assertBuildsCreated(2)
        self.assertEqual(
            u'amd64 build of baz 1.0-1 in ubuntu warty SECURITY',
            build_used.title)

        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

    def testBuildLookup(self):
        """Check if an available build gets used when it is appropriate.

        It happens when the security source upload got already published
        when the binary uploads arrive.
        The queue-build has already created build records for it and
        NascentUpload should identify this condition and used them instead
        of creating new ones.
        Also verify that builds for another architecture does not got
        erroneously attached.
        """
        build_right_candidate = self._createBuild('i386')
        build_wrong_candidate = self._createBuild('hppa')
        build_used = self._uploadBinary('i386')

        self.assertEqual(build_right_candidate.id, build_used.id)
        self.assertNotEqual(build_wrong_candidate.id, build_used.id)
        self.assertBuildsCreated(2)
        self.assertEqual(
            u'i386 build of baz 1.0-1 in ubuntu warty SECURITY',
            build_used.title)
        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

    def testCorrectBuildPassedViaCommandLine(self):
        """Check if command-line build argument gets attached correctly.

        It's also possible to pass an specific buildid via the command-line
        to be attached to the current upload.

        This is only used in 'buildd' policy and does not produce very useful
        results in 'security', however we want to check if it, at least,
        does not 'break the system' entirely.
        """
        build_candidate = self._createBuild('i386')
        self.options.buildid = str(build_candidate.id)
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        build_used = self._uploadBinary('i386')

        self.assertEqual(build_candidate.id, build_used.id)
        self.assertBuildsCreated(1)
        self.assertEqual(
            u'i386 build of baz 1.0-1 in ubuntu warty SECURITY',
            build_used.title)

        self.assertEqual('FULLYBUILT', build_used.buildstate.name)

    def testWrongBuildPassedViaCommandLine(self):
        """Check if a misapplied passed buildid is correctly identified.

        When we identify misapplied build, either by getting it from command
        line or by a failure in lookup methods the upload is rejected before
        anything wrong gets into the DB.
        """
        build_candidate = self._createBuild('hppa')
        self.options.buildid = str(build_candidate.id)
        self.uploadprocessor = UploadProcessor(
            self.options, self.layer.txn, self.log)

        self.assertRaises(AssertionError, self._uploadBinary, 'i386')

        self.assertLogContains(
            "UploadError: Attempt to upload binaries specifying build %d, "
            "where they don't fit.\n" % (build_candidate.id,))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


