# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ApportJobs."""

__metaclass__ = type

import os
import transaction
import unittest

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.testing import LaunchpadFunctionalLayer, LaunchpadZopelessLayer

from lp.bugs.browser.bugtarget import FileBugDataParser
from lp.bugs.interfaces.apportjob import ApportJobType
from lp.bugs.model.apportjob import (
    ApportJob, ApportJobDerived, ProcessApportBlobJob)
from lp.testing import TestCaseWithFactory


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

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(ProcessApportBlobJobTestCase, self).setUp()

        # Create a BLOB using existing testing data.
        testfiles = os.path.join(config.root, 'lib/lp/bugs/tests/testfiles')
        blob_file = open(
            os.path.join(testfiles, 'extra_filebug_data.msg'))
        blob_data = blob_file.read()

        self.blob = self.factory.makeBlob(blob_data)

        self.data_parser = FileBugDataParser(self.blob.file_alias)

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
        filebug_data = self.data_parser.parse()
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



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
