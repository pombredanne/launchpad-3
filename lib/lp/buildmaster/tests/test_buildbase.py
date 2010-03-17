# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

"""Tests for `IBuildBase`."""

__metaclass__ = type

from datetime import datetime
import os
import shutil
import tempfile
import unittest

from canonical.config import config
from canonical.launchpad.scripts import BufferLogger
from canonical.testing.layers import DatabaseFunctionalLayer, LaunchpadZopelessLayer
from lp.buildmaster.model.buildbase import BuildBase
from lp.testing import TestCase, TestCaseWithFactory


class TestBuildBase(TestCase):
    """Tests for `IBuildBase`."""

    def test_getUploadLeaf(self):
        # getUploadLeaf returns the current time, followed by the build id.
        build_base = BuildBase()
        now = datetime.now()
        build_id = self.factory.getUniqueInteger()
        upload_leaf = build_base.getUploadLeaf(build_id, now=now)
        self.assertEqual(
            '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_id), upload_leaf)

    def test_getUploadDir(self):
        # getUploadDir is the absolute path to the directory in which things
        # are uploaded to.
        build_base = BuildBase()
        build_id = self.factory.getUniqueInteger()
        upload_leaf = build_base.getUploadLeaf(build_id)
        upload_dir = build_base.getUploadDir(upload_leaf)
        self.assertEqual(
            os.path.join(config.builddmaster.root, 'incoming', upload_leaf),
            upload_dir)


class TestBuildBaseWithDatabase(TestCaseWithFactory):
    """Tests for `IBuildBase` that need objects from the rest of Launchpad."""

    layer = DatabaseFunctionalLayer

    def test_getUploadLogContent_nolog(self):
        """If there is no log file there, a string explaining that is returned.
        """
        self.useTempDir()
        build_base = BuildBase()
        self.assertEquals('Could not find upload log file', 
            build_base.getUploadLogContent(os.getcwd(), "myleaf"))

    def test_getUploadLogContent_only_dir(self):
        """If there is a directory but no log file, expect the error string,
        not an exception."""
        self.useTempDir()
        os.makedirs("accepted/myleaf")
        build_base = BuildBase()
        self.assertEquals('Could not find upload log file', 
            build_base.getUploadLogContent(os.getcwd(), "myleaf"))

    def test_getUploadLogContent_readsfile(self):
        """If there is a log file, return its contents."""
        self.useTempDir()
        os.makedirs("accepted/myleaf")
        with open('accepted/myleaf/uploader.log', 'w') as f:
            f.write('foo')
        build_base = BuildBase()
        self.assertEquals('foo',
            build_base.getUploadLogContent(os.getcwd(), "myleaf"))


class TestProcessUpload(TestCaseWithFactory):
    """Test the execution of process-upload."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.queue_location = tempfile.mkdtemp()
        self.leaf = "theleaf"
        os.mkdir(os.path.join(self.queue_location, self.leaf))
        super(TestProcessUpload, self).setUp()
        self.build_base = BuildBase()
        self.build_base.distroseries = self.factory.makeDistroSeries()
        self.build_base.distribution = self.build_base.distroseries.distribution
        self.build_base.pocket = self.factory.getAnyPocket()
        self.build_base.id = self.factory.getUniqueInteger()
        self.build_base.policy_name = "insecure"

    def tearDown(self):
        super(TestProcessUpload, self).tearDown()
        shutil.rmtree(self.queue_location)

    def assertQueuePath(self, path):
        """Check if given path exists within the current queue_location."""
        probe_path = os.path.join(self.queue_location, path)
        self.assertTrue(
            os.path.exists(probe_path), "'%s' does not exist." % path)

    def testSimpleRun(self):
        """Try a simple process-upload run.

        Observe it creating the required directory tree for a given
        empty queue_location.
        """
        logger = BufferLogger()
        self.build_base.processUpload(self.leaf,
            os.path.join(self.queue_location, "mylog"),
            self.queue_location, logger)

        # Directory tree in place.
        for directory in ['incoming', 'accepted', 'rejected', 'failed']:
            self.assertQueuePath(directory)

        # Just to check if local assertion is working as expect.
        self.assertRaises(AssertionError, self.assertQueuePath, 'foobar')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
