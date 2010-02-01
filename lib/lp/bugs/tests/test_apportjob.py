# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for ApportJobs."""

__metaclass__ = type

import os
import unittest

from canonical.config import config
from canonical.testing import LaunchpadZopelessLayer

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

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(ProcessApportBlobJobTestCase, self).setUp()

        # Create a BLOB using existing testing data.
        testfiles = os.path.join(config.root, 'lib/lp/bugs/tests/testfiles')
        blob_data = open(
            os.path.join(testfiles, 'extra_filebug_data.msg')).read()
        self.blob = self.factory.makeBlob(blob_data)

    def test_run(self):
        # ProcessApportBlobJob.run() extracts salient data from an
        # Apport BLOB and stores it in the job's metadata attribute.
        job = ProcessApportBlobJob.create(self.blob)
        job.run()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
