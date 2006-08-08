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
from importd.tests.helpers import SandboxTestCase
from importd.tests.testutil import makeSilentLogger


class TestSourceTransportScripts(SandboxTestCase):
    """Test that the script front-ends for ImportdSourceTransport work."""

    def setUp(self):
        SandboxTestCase.setUp(self)
        self.local_source = self.sandbox.join('fooworking')
        self.remote_dir = self.sandbox.join('remote')
        os.mkdir(self.remote_dir)
        self.remote_tarball = self.sandbox.join('remote', 'fooworking.tgz')
        self.logger = makeSilentLogger()
        self.transport = ImportdSourceTransport(
            self.logger, self.local_source, self.remote_dir)

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
        retcode = subprocess.call(
            ['tar', 'czf', self.remote_tarball, self.local_source])
        assert retcode == 0
        shutil.rmtree(source)

    def test_importdGetSource(self):
        # Check that the importd-get-source.py script runs and does something
        # that looks right. That ensures there is no trivial bug in the script.
        self.setUpTarball()
        assert not os.path.exists(self.local_source)
        self.runScript('importd-get-source.py')
        self.assertTrue(os.path.isdir(self.local_source))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
