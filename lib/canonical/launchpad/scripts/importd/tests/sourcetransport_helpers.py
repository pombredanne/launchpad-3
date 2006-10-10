# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helpers and base classes for testing ImportdSourceTransport.
"""

__metaclass__ = type

__all__ = [
    'test_suite',
    'ImportdSourceTransportTestCase',
    'ImportdSourceTarballTestCase',
    ]


import os
import shutil
import subprocess
import unittest

from bzrlib.urlutils import local_path_to_url

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
            self.logger, self.local_source, local_path_to_url(self.remote_dir))

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


class ImportdSourceTarballTestCase(ImportdSourceTransportTestCase):
    """Base for ImportdSourceTransport tests that care about tarball contents.
    """

    def setUpLocalSource(self):
        """Create a local_source directory with one distinctive file."""
        os.mkdir(self.local_source)
        source_path = os.path.join(self.local_source, 'hello')
        self.writeDistinctiveData(source_path)

    def setUpRemoteTarball(self):
        """Create remote_tarball with the expected contents."""
        self.setUpLocalSource()
        source_parent, source_name = os.path.split(self.local_source)
        retcode = subprocess.call(
            ['tar', 'czf', self.remote_tarball, source_name,
             '-C', source_parent])
        assert retcode == 0, 'tar exited with status %d' % retcode
        shutil.rmtree(self.local_source)

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

    def testAssertTarballMatchesSource(self):
        # Check that setUpRemoteTarball and assertTarballMatchesSource are
        # consistent.
        self.setupRemoteTarball()
        self.assertTarballMatchesSource(self.remote_tarball)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
