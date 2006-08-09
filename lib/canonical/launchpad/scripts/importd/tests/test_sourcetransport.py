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
        self.remote_dir = self.sandbox.join('remote')
        os.mkdir(self.remote_dir)
        self.remote_tarball = self.sandbox.join('remote', 'fooworking.tgz')
        self.transport = ImportdSourceTransport(
            self.logger, self.local_source, self.remote_dir)

    def tearDown(self):
        SandboxTestCase.tearDown(self)
        # reset_logging is needed because makeSilentLogger alters the state of
        # the logging framework
        reset_logging()


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


class TestPutImportdSource(ImportdSourceTransportTestCase):
    """Test ImportdSourceTransport.putImportdSource."""

    # TODO: unit test creation of remote directory

    # TODO: unit test failure when parent of remote directory does not exist

    # TODO: unit test that non-finalized upload does not overwrite existing
    # tarball

    # TODO: unit test that finalizing upload replaces existing tarball

    # TODO: unit test deletion of files other than the final tarball

    # TODO: test correct call sequence to helpers used in all unit tests

    def setUpLocalSource(self):
        """Create a local_source directory with one distinctive file."""
        os.mkdir(self.local_source)
        source_path = os.path.join(self.local_source, 'hello')
        source_file = open(source_path, 'w')
        source_file.write("Hello, World!\n")
        source_file.close()

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
        source_file = open(source_file_path)
        self.assertEqual(source_file.read(), "Hello, World!\n")
        source_file.close()

    def testAssertGoodSourcePresent(self):
        # Check that setUpLocalSource and assertGoodSourcePresent are
        # consistent.
        self.setUpLocalSource()
        self.assertGoodSourcePresent(self.sandbox.path)

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
        self.assertTarballMatchesSource(self.local_source + '.tgz')

    # TODO: unit test that existing local tarball is deleted prior to creating
    # new one



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
