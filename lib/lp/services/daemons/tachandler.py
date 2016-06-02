# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for TAC (Twisted Application Configuration) files."""

__metaclass__ = type

__all__ = [
    'TacTestSetup',
    'TacException',
    ]


import os
import sys

from txfixtures.tachandler import (
    TacException,
    TacTestFixture,
    )

import lp
from lp.services.daemons import readyservice
from lp.services.osutils import (
    override_environ,
    remove_if_exists,
    )


twistd_script = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'twistd'))


class TacTestSetup(TacTestFixture):
    """Setup an TAC file as daemon for use by functional tests.

    You must override setUpRoot to set up a root directory for the daemon.
    """

    def setUp(self, spew=False, umask=None):
        # setUp() watches the logfile to determine when the daemon has fully
        # started. If it sees an old logfile, then it will find the
        # readyservice.LOG_MAGIC string and return immediately, provoking
        # hard-to-diagnose race conditions. Delete the logfile to make sure
        # this does not happen.
        self.removeLog()
        with override_environ(LP_DEBUG_SQL=None):
            TacTestFixture.setUp(self,
                python_path=sys.executable,
                twistd_script=twistd_script)

    def _hasDaemonStarted(self):
        """Has the daemon started?

        Startup is recognized by the appearance of readyservice.LOG_MAGIC in
        the log file.
        """
        if os.path.exists(self.logfile):
            with open(self.logfile, 'r') as logfile:
                return readyservice.LOG_MAGIC in logfile.read()
        else:
            return False

    def removeLog(self):
        remove_if_exists(self.logfile)

    def truncateLog(self):
        """Truncate the log file.

        Leaves everything up to and including the `LOG_MAGIC` marker in
        place. If the `LOG_MAGIC` marker is not found the log is truncated to
        0 bytes.
        """
        if os.path.exists(self.logfile):
            with open(self.logfile, "r+b") as logfile:
                position = 0
                for line in logfile:
                    position += len(line)
                    if readyservice.LOG_MAGIC in line:
                        logfile.truncate(position)
                        break
                else:
                    logfile.truncate(0)

    @property
    def daemon_directory(self):
        return os.path.abspath(
            os.path.join(os.path.dirname(lp.__file__), os.pardir, os.pardir,
            'daemons'))

    def setUpRoot(self):
        """Override this.

        This should be able to cope with the root already existing, because it
        will be left behind after each test in case it's needed to diagnose a
        test failure (e.g. log files might contain helpful tracebacks).
        """
        raise NotImplementedError
