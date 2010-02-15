# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ApportJobs."""

__metaclass__ = type

import os
import transaction
import unittest

from sqlobject import SQLObjectNotFound

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.temporaryblobstorage import (
    ITemporaryStorageManager)
from canonical.launchpad.webapp.interfaces import ILaunchpadRoot
from canonical.launchpad.scripts.tests import run_script
from canonical.testing import (
    LaunchpadFunctionalLayer, LaunchpadZopelessLayer)

from lp.bugs.interfaces.apportjob import ApportJobType
from lp.bugs.model.apportjob import (
    ApportJob, ApportJobDerived, ProcessApportBlobJob)
from lp.bugs.utilities.filebugdataparser import FileBugDataParser
from lp.services.job.interfaces.job import JobStatus
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view


class ApportJobTestCase(TestCaseWithFactory):
    """Test case for basic ApportJob gubbins."""

    layer = LaunchpadZopelessLayer

    def test_instantiate(self):
        # ApportJob.__init__() instantiates a ApportJob instance.
        blob = self.factory.makeBlob()

        metadata = ('some', 'arbitrary', 'metadata')
        apport_job = ApportJob(
            blob, ApportJobType.PROCESS_BLOB, metadata)

        self.assertEqual(blob, apport_job.blob)
        self.assertEqual(ApportJobType.PROCESS_BLOB, apport_job.job_type)

        # When we actually access the ApportJob's metadata it gets
        # unserialized from JSON, so the representation returned by
        # apport_job.metadata will be different from what we originally
        # passed in.
        metadata_expected = [u'some', u'arbitrary', u'metadata']
        self.assertEqual(metadata_expected, apport_job.metadata)


class ApportJobDerivedTestCase(TestCaseWithFactory):
    """Test case for the ApportJobDerived class."""

    layer = LaunchpadZopelessLayer

    def test_create_explodes(self):
        # ApportJobDerived.create() will blow up because it needs to be
        # subclassed to work properly.
        blob = self.factory.makeBlob()
        self.assertRaises(
            AttributeError, ApportJobDerived.create, blob)


class ProcessApportBlobJobTestCase(TestCaseWithFactory):
    """Test case for the ProcessApportBlobJob class."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(ProcessApportBlobJobTestCase, self).setUp()

        # Create a BLOB using existing testing data.
        testfiles = os.path.join(config.root, 'lib/lp/bugs/tests/testfiles')
        blob_file = open(
            os.path.join(testfiles, 'extra_filebug_data.msg'))
        blob_data = blob_file.read()

        self.blob = self.factory.makeBlob(blob_data)

    def test_run(self):
        # ProcessApportBlobJob.run() extracts salient data from an
        # Apport BLOB and stores it in the job's metadata attribute.
        job = ProcessApportBlobJob.create(self.blob)
        job.run()
        transaction.commit()

        # Once the job has been run, its metadata will contain a dict
        # called processed_data, which will contain the data parsed from
        # the BLOB.
        processed_data = job.metadata.get('processed_data', None)
        self.assertNotEqual(
            None, processed_data,
            "processed_data should not be None after the job has run.")

        # The items in the processed_data dict represent the salient
        # information parsed out of the BLOB. We can use our
        # FileBugDataParser to check that the items recorded in the
        # processed_data dict are correct.
        self.blob.file_alias.open()
        data_parser = FileBugDataParser(self.blob.file_alias)
        filebug_data = data_parser.parse()

        self.assertEqual(
            filebug_data.initial_summary, processed_data['initial_summary'],
            "Initial summaries do not match")
        self.assertEqual(
            filebug_data.initial_tags, processed_data['initial_tags'],
            "Values for initial_tags do not match")
        self.assertEqual(
            filebug_data.private, processed_data['private'],
            "Values for private do not match")
        self.assertEqual(
            filebug_data.subscribers, processed_data['subscribers'],
            "Values for subscribers do not match")
        self.assertEqual(
            filebug_data.extra_description,
            processed_data['extra_description'],
            "Values for extra_description do not match")
        self.assertEqual(
            filebug_data.comments, processed_data['comments'],
            "Values for comments do not match")
        self.assertEqual(
            filebug_data.hwdb_submission_keys,
            processed_data['hwdb_submission_keys'],
            "Values for hwdb_submission_keys do not match")

        # The attachments list of of the processed_data dict will be of
        # the same length as the attachments list in the filebug_data
        # object.
        self.assertEqual(
            len(filebug_data.attachments),
            len(processed_data['attachments']),
            "Lengths of attachment lists do not match.")

        # The attachments list of the processed_data dict contains the
        # IDs of LibrarianFileAliases that contain the attachments
        # themselves. The contents, filenames and filetypes of the files
        # in the librarian will match the contents of the attachments.
        for file_alias_id in processed_data['attachments']:
            file_alias = getUtility(ILibraryFileAliasSet)[file_alias_id]
            attachment = filebug_data.attachments[
                processed_data['attachments'].index(file_alias_id)]

            file_content = attachment['content'].read()
            librarian_file_content = file_alias.read()
            self.assertEqual(
                file_content, librarian_file_content,
                "File content values do not match for attachment %s and "
                "LibrarianFileAlias %s" % (
                    attachment['filename'], file_alias.filename))
            self.assertEqual(
                attachment['filename'], file_alias.filename,
                "Filenames do not match for attachment %s and "
                "LibrarianFileAlias %s" % (
                    attachment['filename'], file_alias.id))
            self.assertEqual(
                attachment['content_type'], file_alias.mimetype,
                "Content types do not match for attachment %s and "
                "LibrarianFileAlias %s" % (
                    attachment['filename'], file_alias.id))

    def test_getByBlobUUID(self):
        # ProcessApportBlobJob.getByBlobUUID takes a BLOB UUID as a
        # parameter and returns any jobs for that BLOB.
        uuid = self.blob.uuid

        job = ProcessApportBlobJob.create(self.blob)
        job_from_uuid = ProcessApportBlobJob.getByBlobUUID(uuid)
        self.assertEqual(
            job, job_from_uuid,
            "Job returend by getByBlobUUID() did not match original job.")
        self.assertEqual(
            self.blob, job_from_uuid.blob,
            "BLOB referenced by Job returned by getByBlobUUID() did not "
            "match original BLOB.")

        # If the UUID doesn't exist, getByBlobUUID() will raise a
        # SQLObjectNotFound error.
        self.assertRaises(
            SQLObjectNotFound, ProcessApportBlobJob.getByBlobUUID, 'foobar')

    def test_create_job_creates_only_one(self):
        # ProcessApportBlobJob.create() will create only one
        # ProcessApportBlobJob for a given BLOB, no matter how many
        # times it is called.
        current_jobs = list(ProcessApportBlobJob.iterReady())
        self.assertEqual(
            0, len(current_jobs),
            "There should be no ProcessApportBlobJobs. Found %s" %
            len(current_jobs))

        job = ProcessApportBlobJob.create(self.blob)
        current_jobs = list(ProcessApportBlobJob.iterReady())
        self.assertEqual(
            1, len(current_jobs),
            "There should be only one ProcessApportBlobJob. Found %s" %
            len(current_jobs))

        another_job = ProcessApportBlobJob.create(self.blob)
        current_jobs = list(ProcessApportBlobJob.iterReady())
        self.assertEqual(
            1, len(current_jobs),
            "There should be only one ProcessApportBlobJob. Found %s" %
            len(current_jobs))

        # If the job is complete, it will no longer show up in the list
        # of ready jobs. However, it won't be possible to create a new
        # job to process the BLOB because each BLOB can only have one
        # ProcessApportBlobJob.
        job.job.start()
        job.job.complete()
        current_jobs = list(ProcessApportBlobJob.iterReady())
        self.assertEqual(
            0, len(current_jobs),
            "There should be no ready ProcessApportBlobJobs. Found %s" %
            len(current_jobs))

        yet_another_job = ProcessApportBlobJob.create(self.blob)
        current_jobs = list(ProcessApportBlobJob.iterReady())
        self.assertEqual(
            0, len(current_jobs),
            "There should be no new ProcessApportBlobJobs. Found %s" %
            len(current_jobs))

        # In fact, yet_another_job will be the same job as before, since
        # it's attached to the same BLOB.
        self.assertEqual(job.id, yet_another_job.id, "Jobs do not match.")

    def test_cronscript_succeeds(self):
        # The process-apport-blobs cronscript will run all pending
        # ProcessApportBlobJobs.
        ProcessApportBlobJob.create(self.blob)
        transaction.commit()

        retcode, stdout, stderr = run_script(
            'cronscripts/process-apport-blobs.py', [],
            expect_returncode=0)
        self.assertEqual('', stdout)
        self.assertIn(
            'INFO    Ran 1 IProcessApportBlobJobSource jobs.\n', stderr)


class TestTemporaryBlobStorageAddView(TestCaseWithFactory):
    """Test case for the TemporaryBlobStorageAddView."""

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestTemporaryBlobStorageAddView, self).setUp()

        # Create a BLOB using existing testing data.
        testfiles = os.path.join(config.root, 'lib/lp/bugs/tests/testfiles')
        blob_file = open(
            os.path.join(testfiles, 'extra_filebug_data.msg'))
        self.blob_data = blob_file.read()
        blob_file.close()

        person = self.factory.makePerson()
        self.product = self.factory.makeProduct()
        login_person(person)

    def _create_blob_and_job_using_storeblob(self):
        """Helper method to create a BLOB and ProcessApportBlobJob."""
        view = create_initialized_view(
            getUtility(ILaunchpadRoot), '+storeblob')

        # The view's store_blob method stores the blob in the database
        # and returns its UUID.
        blob_uuid = view.store_blob(self.blob_data)
        transaction.commit()

        return blob_uuid

    def _create_and_traverse_filebug_view(self, blob_uuid):
        """Create a +filebug view for a given blob id and return it."""
        view = create_initialized_view(
            self.product, '+filebug', path_info='/%s' % blob_uuid)

        # We need to call publishTraverse() on the view to ensure that
        # the extra_data_token attribute gets populated.
        view.publishTraverse(view.request, blob_uuid)
        return view

    def test_adding_blob_adds_job(self):
        # Using the TemporaryBlobStorageAddView to upload a new BLOB
        # will add a new ProcessApportBlobJob for that BLOB.
        blob_uuid = self._create_blob_and_job_using_storeblob()
        blob = getUtility(ITemporaryStorageManager).fetch(blob_uuid)
        job = ProcessApportBlobJob.getByBlobUUID(blob_uuid)

        self.assertEqual(
            blob, job.blob,
            "BLOB attached to Job returned by getByBlobUUID() did not match "
            "expected BLOB.")

    def test_filebug_extra_data_processing_job(self):
        # The +filebug view can retrieve the ProcessApportBlobJob for a
        # given BLOB UUID. This is available via its
        # extra_data_processing_job property.
        blob_uuid = self._create_blob_and_job_using_storeblob()
        view = self._create_and_traverse_filebug_view(blob_uuid)

        job = ProcessApportBlobJob.getByBlobUUID(blob_uuid)
        job_from_view = view.extra_data_processing_job
        self.assertEqual(job, job_from_view, "Jobs didn't match.")

        # If a non-existent UUID is passed to +filebug, its
        # extra_data_processing_job property will return None.
        view = create_initialized_view(
            self.product, '+filebug', path_info='/nonsense')
        job_from_view = view.extra_data_processing_job
        self.assertEqual(
            None, job_from_view,
            "Job returned by extra_data_processing_job should be None.")

    def test_filebug_extra_data_processed(self):
        # The +filebug view has a property, extra_data_processed, which
        # indicates whether or not an Apport blob has been processed.
        blob_uuid = self._create_blob_and_job_using_storeblob()
        view = self._create_and_traverse_filebug_view(blob_uuid)

        job_from_view = view.extra_data_processing_job

        # Because the job hasn't yet been run the view's extra_data_processed
        # property will return False.
        self.assertEqual(
            JobStatus.WAITING, job_from_view.job.status,
            "Job should be WAITING, is in fact %s" %
            job_from_view.job.status.title)
        self.assertFalse(
            view.extra_data_processed,
            "view.extra_data_processed should be False while job is WAITING.")

        # If the job is started bug hasn't completed, extra_data_processed
        # will remain False.
        job_from_view.job.start()
        self.assertEqual(
            JobStatus.RUNNING, job_from_view.job.status,
            "Job should be RUNNING, is in fact %s" %
            job_from_view.job.status.title)
        self.assertFalse(
            view.extra_data_processed,
            "view.extra_data_processed should be False while job is RUNNING.")

        # Once the job is complete, extra_data_processed will be True
        job_from_view.job.complete()
        self.assertEqual(
            JobStatus.COMPLETED, job_from_view.job.status,
            "Job should be COMPLETED, is in fact %s" %
            job_from_view.job.status.title)
        self.assertTrue(
            view.extra_data_processed,
            "view.extra_data_processed should be True when job is COMPLETED.")


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
