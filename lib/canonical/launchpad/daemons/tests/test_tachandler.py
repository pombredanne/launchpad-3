# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for canonical.launchpad.daemons.tachandler"""

__metaclass__ = type

from os.path import (
    dirname,
    join,
    )
import subprocess
import warnings

from fixtures import TempDir
import testtools

from canonical.launchpad.daemons.tachandler import (
    TacException,
    TacTestSetup,
    )


class SimpleTac(TacTestSetup):

    def __init__(self, name, tempdir):
        super(SimpleTac, self).__init__()
        self.name, self.tempdir = name, tempdir

    @property
    def root(self):
        return dirname(__file__)

    @property
    def tacfile(self):
        return join(self.root, '%s.tac' % self.name)

    @property
    def pidfile(self):
        return join(self.tempdir, '%s.pid' % self.name)

    @property
    def logfile(self):
        return join(self.tempdir, '%s.log' % self.name)

    def setUpRoot(self):
        pass


class TacTestSetupTestCase(testtools.TestCase):
    """Some tests for the error handling of TacTestSetup."""

    def test_missingTac(self):
        """TacTestSetup raises TacException if the tacfile doesn't exist"""

        class MissingTac(TacTestSetup):

            root = '/'
            tacfile = '/file/does/not/exist'
            pidfile = tacfile
            logfile = tacfile

            def setUpRoot(self):
                pass

        fixture = MissingTac()
        try:
            self.assertRaises(TacException, fixture.setUp)
        finally:
            fixture.cleanUp()

    def test_couldNotListenTac(self):
        """If the tac fails due to not being able to listen on the needed
        port, TacTestSetup will fail.
        """
        tempdir = self.useFixture(TempDir()).path

        class CouldNotListenTac(TacTestSetup):

            root = dirname(__file__)
            tacfile = join(root, 'cannotlisten.tac')
            pidfile = join(tempdir, 'cannotlisten.pid')
            logfile = join(tempdir, 'cannotlisten.log')

            def setUpRoot(self):
                pass

        fixture = CouldNotListenTac()
        try:
            self.assertRaises(TacException, fixture.setUp)
        finally:
            fixture.cleanUp()

    def test_pidForNotRunningProcess(self):
        """TacTestSetup copes fine if the pidfile contains a stale pid."""
        tempdir = self.useFixture(TempDir()).path
        fixture = SimpleTac("okay", tempdir)

        # Run a short-lived process with the intention of using its pid in the
        # next step. Linux uses pids sequentially (from the information I've
        # been able to discover) so this approach is safe as long as we don't
        # delay until pids wrap... which should be a very long time unless the
        # machine is seriously busy.
        process = subprocess.Popen("true")
        process.wait()

        # Put the (now bogus) pid in the pid file.
        with open(fixture.pidfile, "wb") as pidfile:
            pidfile.write(str(process.pid))

        # Fire up the fixture, capturing warnings.
        with warnings.catch_warnings(record=True) as warnings_log:
            try:
                self.assertRaises(TacException, fixture.setUp)
            finally:
                fixture.cleanUp()

        # One deprecation warning is emitted.
        self.assertEqual(1, len(warnings_log))
        self.assertIs(DeprecationWarning, warnings_log[0].category)
