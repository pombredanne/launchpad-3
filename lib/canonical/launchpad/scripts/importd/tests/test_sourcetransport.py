# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Test canonical.launchpad.scripts.importd.sourcetransport
"""

__metaclass__ = type

__all__ = ['test_suite']


import os
import unittest
import shutil
import subprocess

from canonical.config import config
from canonical.launchpad.scripts.importd.sourcetransport import (
    ImportdSourceTransport)
from canonical.testing import reset_logging
from importd.tests.helpers import SandboxTestCase
from importd.tests.testutil import makeSilentLogger


class ImportdSourceTransportTestCase(SandboxTestCase):
    """Common base for ImportdSourceTransport test cases."""

    def setUp(self):
        SandboxTestCase.setUp(self)
        self.logger = makeSilentLogger()
        self.local_source = self.sandbox.join('fooworking')
        self.local_tarball = self.local_source + '.tgz'
        self.setUpRemoteDir()
        self.setUpTransport()

    def setUpRemoteDir(self):
        """Set and maybe create remote_dir. Set remote_tarball."""
        self.remote_dir = self.sandbox.join('remote')
        os.mkdir(self.remote_dir)
        self.remote_tarball = self.sandbox.join('remote', 'fooworking.tgz')
        self.remote_tarball_swap = self.remote_tarball + '.swp'

    def setUpTransport(self):
        """Instanciate the transport to test.

        Some tests want to postpone that to the test method, after setting up a
        special remote_dir.
        """
        self.transport = ImportdSourceTransport(
            self.logger, self.local_source, self.remote_dir)

    def tearDown(self):
        SandboxTestCase.tearDown(self)
        # reset_logging is needed because makeSilentLogger alters the state of
        # the logging framework
        reset_logging()

    def writeData(self, path, content):
        """Create a file with the specified contents."""
        a_file = open(path, 'w')
        a_file.write(content)
        a_file.close()

    def writeDistinctiveData(self, path):
        """Create a file with distinctive content."""
        self.writeData(path, "Hello, World!\n")

    def assertDistinctiveData(self, path):
        """Check that the path is a file with distinctive content."""
        self.assertTrue(os.path.isfile(path))
        a_file = open(path)
        content = a_file.read()
        a_file.close()
        self.assertEqual(content, "Hello, World!\n")


class TestImportdSourceTransportScripts(ImportdSourceTransportTestCase):
    """Test that the script front-ends for ImportdSourceTransport work."""

    def runScript(self, command):
        """Run the named script, fail if it exits with a non-zero status."""
        script = os.path.join(config.root, 'scripts', command)
        process = subprocess.Popen(
            [script, '-q', self.local_source, self.remote_dir],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=open('/dev/null'))
        output, error = process.communicate()
        status = process.returncode
        self.assertEqual(status, 0,
            '%s existed with status=%d\n'
            '>>>stdout<<<\n%s\n>>>stderr<<<\n%s'
            % (command, status, output, error))

    def test_importdPutSource(self):
        # Check that the importd-put-source.py script runs and does something
        # that looks right. That ensures there is no trivial bug in the script.
        os.mkdir(self.local_source)
        assert not os.path.exists(self.remote_tarball)
        self.runScript('importd-put-source.py')
        self.assertTrue(os.path.isfile(self.remote_tarball))

    def setUpTarball(self):
        """Create an appropriate tarball in remote_dir.

        It must have a name based on local_source and it must contain a single
        directory whose name is the basename of local_source.
        """
        source = self.local_source
        assert not os.path.exists(source)
        os.mkdir(source)
        source_parent, source_name = os.path.split(self.local_source)
        retcode = subprocess.call(
            ['tar', 'czf',
             self.remote_tarball, source_name, '-C', source_parent])
        assert retcode == 0
        shutil.rmtree(source)

    def test_importdGetSource(self):
        # Check that the importd-get-source.py script runs and does something
        # that looks right. That ensures there is no trivial bug in the script.
        self.setUpTarball()
        assert not os.path.exists(self.local_source)
        self.runScript('importd-get-source.py')
        self.assertTrue(os.path.isdir(self.local_source))


class ImportdSourceTarballTestCase(ImportdSourceTransportTestCase):
    """Base for ImportdSourceTransport tests that care about tarball contents.
    """

    def setUpLocalSource(self):
        """Create a local_source directory with one distinctive file."""
        os.mkdir(self.local_source)
        source_path = os.path.join(self.local_source, 'hello')
        self.writeDistinctiveData(source_path)

    def assertTarballMatchesSource(self, tarball):
        """Check that the remote_tarball has the expected contents."""
        tarball_dir = self.sandbox.join('tarball')
        os.mkdir(tarball_dir)
        retcode = subprocess.call(
            ['tar', 'xzf', tarball, '-C', tarball_dir])
        self.assertEqual(retcode, 0)
        self.assertGoodSourcePresent(tarball_dir)
        shutil.rmtree(tarball_dir)

    def assertGoodSourcePresent(self, directory):
        """Check that directory contains a good source tree.

        The source tree must have the name and contents created by
        setUpLocalSource.
        """
        source_dir_name = os.path.basename(self.local_source)
        self.assertTrue(source_dir_name in os.listdir(directory))
        source_dir = os.path.join(directory, source_dir_name)
        source_file_name = 'hello'
        self.assertEqual(os.listdir(source_dir), [source_file_name])
        source_file_path = os.path.join(source_dir, source_file_name)
        self.assertDistinctiveData(source_file_path)


class TestImportdSourceTarballTestCase(ImportdSourceTarballTestCase):
    """Check that ImportdSourceTarballTestCase methods are consistent."""

    def testAssertGoodSourcePresent(self):
        # Check that setUpLocalSource and assertGoodSourcePresent are
        # consistent.
        self.setUpLocalSource()
        self.assertGoodSourcePresent(self.sandbox.path)


class TestPutImportdSourceTarball(ImportdSourceTarballTestCase):
    """Tests for putImportdSource that care about tarball contents."""

    def testPutImportdSource(self):
        # Check that putImportdSource creates a tarball at the expected
        # location with the contents of the source tree.
        self.setUpLocalSource()
        self.transport.putImportdSource()
        self.assertTarballMatchesSource(self.remote_tarball)

    def testCreateTarball(self):
        # Check that _createTarball creates a tarball with the contents of the
        # source tree.
        self.setUpLocalSource()
        self.transport._createTarball()
        self.assertTarballMatchesSource(self.local_tarball)

    def testOverwriteTarball(self):
        # Check that _createTarball overwrites any existing file using the name
        # of the tarball.
        self.setUpLocalSource()
        # We create a non-tarball file in place of the tarball, so if it is not
        # entirely overwritten, either the creation or the verification of the
        # tarball will fail.
        not_tarball = open(self.local_tarball, 'w')
        not_tarball.write("invalid content\n")
        not_tarball.close()
        # Now, _createTarball must still create the content we expect.
        self.transport._createTarball()
        self.assertTarballMatchesSource(self.local_tarball)


class TestPutImportdSourceUploadTarball(ImportdSourceTransportTestCase):
    """Tests that putImportdSource properly creates the remote dir."""

    def setUpRemoteDir(self):
        """Do nothing. Delegate to individual test methods."""

    def setUpTransport(self):
        """Do nothing. Delegate to individual test methods."""

    def testUploadTarball(self):
        # Check that _uploadTarball sends the tarball data to the remote_dir,
        # in a swap file. We use a temporary swap file so failed uploads do not
        # erase the existing tarball. The remote transport might already
        # provide this guarantee, but it would be hard for us to test.
        ImportdSourceTransportTestCase.setUpRemoteDir(self)
        ImportdSourceTransportTestCase.setUpTransport(self)
        assert os.path.exists(self.remote_dir)
        # We use the nice default fixture where remote_dir exists.
        self.writeDistinctiveData(self.local_tarball)
        self.transport._uploadTarball()
        self.assertDistinctiveData(self.remote_tarball_swap)

    def testCreateRemoteDir(self):
        # Check that _uploadTarball creates the remote directory if needed.
        # Setup a non-existing remote_dir whose parent exists.
        self.remote_dir = self.sandbox.join('remote', 'subdir')
        os.mkdir(os.path.dirname(self.remote_dir))
        self.remote_tarball_swap = os.path.join(
            self.remote_dir, 'fooworking.tgz.swp')
        ImportdSourceTransportTestCase.setUpTransport(self)
        # Make sure we actually have the right setup
        assert not os.path.exists(self.remote_dir)
        assert os.path.isdir(os.path.dirname(self.remote_dir))
        # _uploadTarball must create the remote_dir and upload the file
        self.writeDistinctiveData(self.local_tarball)
        self.transport._uploadTarball()
        self.assertTrue(os.path.isdir(self.remote_dir))
        self.assertDistinctiveData(self.remote_tarball_swap)

    def testFinalizeUpload(self):
        # Check that _finalizeUpload renames the remote swap file to the remote
        # tarball name even if the remote tarball is already present.
        ImportdSourceTransportTestCase.setUpRemoteDir(self)
        ImportdSourceTransportTestCase.setUpTransport(self)
        self.writeDistinctiveData(self.remote_tarball_swap)
        self.writeData(self.remote_tarball, "Bad data\n")
        self.transport._finalizeUpload()
        self.assertFalse(os.path.exists(self.remote_tarball_swap))
        self.assertDistinctiveData(self.remote_tarball)

    def testCleanUpRemoteDir(self):
        # _cleanUpRemoteDir deletes any file present in remote_dir, except the
        # final tarball that it must leave untouched. Deleting unknown files is
        # needed because the bzrlib transport may use random temporary names
        # during the upload, and we do not want to let failed uploads
        # accumulate cruft.
        ImportdSourceTransportTestCase.setUpRemoteDir(self)
        ImportdSourceTransportTestCase.setUpTransport(self)
        self.writeDistinctiveData(self.remote_tarball)
        self.writeData(self.remote_tarball_swap, "Swap data\n")
        random_path = os.path.join(self.remote_dir, 'random')
        self.writeData(random_path, "Random data\n")
        # Make sure we have created the files in the same place.
        remote_names = os.listdir(self.remote_dir)
        expected_names = [os.path.basename(path) for path in
            [self.remote_tarball_swap, self.remote_tarball, random_path]]
        assert sorted(remote_names) == sorted(expected_names)
        # Run _cleanupRemoteDir and check that only the tarball is left, and
        # that it was untouched.
        self.transport._cleanUpRemoteDir()
        remote_names = os.listdir(self.remote_dir)
        self.assertEqual(remote_names, [os.path.basename(self.remote_tarball)])
        self.assertDistinctiveData(self.remote_tarball)

    def testCleanupRemoteDirMissing(self):
        # _cleanUpRemoteDir must work even if the remote_dir does not exist,
        # because it is run before trying to upload the tarball.
        self.remote_dir = self.sandbox.join('remote')
        ImportdSourceTransportTestCase.setUpTransport(self)
        # Make sure the remote_dir does not exist
        assert not os.path.exists(self.remote_dir)
        # call _cleanUpRemoteDir, it should do nothing
        self.transport._cleanUpRemoteDir()

# TODO: feature test getImportdSource can download and install tarball

# TODO: unit test initial cleanup

# TODO: unit test downloading the tarball

# TODO: unit test expanding the tarball

# TODO: feature test transition: getImportdSource does putImportdSource if the
# remote tarball is missing and there is a local source tree.

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
