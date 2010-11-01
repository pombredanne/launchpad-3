# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test harness for TAC (Twisted Application Configuration) files."""

__metaclass__ = type

__all__ = [
    'TacTestSetup',
    'TacException',
    'kill_by_pidfile',
    'remove_if_exists',
    'two_stage_kill',
    ]


import errno
import os
from signal import (
    SIGKILL,
    SIGTERM,
    )
import subprocess
import sys
import time
import warnings

from fixtures import Fixture
from twisted.application import service
from twisted.python import log

from canonical.launchpad.daemons import readyservice


def _kill_may_race(pid, signal_number):
    """Kill a pid accepting that it may not exist."""
    try:
        os.kill(pid, signal_number)
    except OSError, e:
        if e.errno in (errno.ESRCH, errno.ECHILD):
            # Process has already been killed.
            return
        # Some other issue (e.g. different user owns it)
        raise


def two_stage_kill(pid, poll_interval=0.1, num_polls=50):
    """Kill process 'pid' with SIGTERM. If it doesn't die, SIGKILL it.

    :param pid: The pid of the process to kill.
    :param poll_interval: The polling interval used to check if the
        process is still around.
    :param num_polls: The number of polls to do before doing a SIGKILL.
    """
    # Kill the process.
    _kill_may_race(pid, SIGTERM)

    # Poll until the process has ended.
    for i in range(num_polls):
        try:
            # Reap the child process and get its return value. If it's not
            # gone yet, continue.
            new_pid, result = os.waitpid(pid, os.WNOHANG)
            if new_pid:
                return result
            time.sleep(poll_interval)
        except OSError, e:
            if e.errno in (errno.ESRCH, errno.ECHILD):
                # Raised if the process is gone by the time we try to get the
                # return value.
                return

    # The process is still around, so terminate it violently.
    _kill_may_race(pid, SIGKILL)


def get_pid_from_file(pidfile_path):
    """Retrieve the PID from the given file, if it exists, None otherwise."""
    if not os.path.exists(pidfile_path):
        return None
    # Get the pid.
    pid = open(pidfile_path, 'r').read().split()[0]
    try:
        pid = int(pid)
    except ValueError:
        # pidfile contains rubbish
        return None
    return pid


def kill_by_pidfile(pidfile_path, poll_interval=0.1, num_polls=50):
    """Kill a process identified by the pid stored in a file.

    The pid file is removed from disk.
    """
    try:
        pid = get_pid_from_file(pidfile_path)
        if pid is None:
            return
        two_stage_kill(pid, poll_interval, num_polls)
    finally:
        remove_if_exists(pidfile_path)


def remove_if_exists(path):
    """Remove the given file if it exists."""
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise


twistd_script = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    os.pardir, os.pardir, os.pardir, os.pardir, 'bin', 'twistd'))


class TacException(Exception):
    """Error raised by TacTestSetup."""


class TacTestSetup(Fixture):
    """Setup an TAC file as daemon for use by functional tests.

    You must override setUpRoot to set up a root directory for the daemon.
    """

    def setUp(self, spew=False, umask=None):
        Fixture.setUp(self)
        if get_pid_from_file(self.pidfile):
            # An attempt to run while there was an existing live helper
            # was made. Note that this races with helpers which use unique
            # roots, so when moving/eliminating this code check subclasses
            # for workarounds and remove those too.
            pid = get_pid_from_file(self.pidfile)
            warnings.warn("Attempt to start Tachandler with an existing "
                "instance (%d) running in %s." % (pid, self.pidfile),
                DeprecationWarning, stacklevel=2)
            two_stage_kill(pid)
            if get_pid_from_file(self.pidfile):
                raise TacException(
                    "Could not kill stale process %s." % (self.pidfile,))

        # setUp() watches the logfile to determine when the daemon has fully
        # started. If it sees an old logfile, then it will find the
        # readyservice.LOG_MAGIC string and return immediately, provoking
        # hard-to-diagnose race conditions. Delete the logfile to make sure
        # this does not happen.
        remove_if_exists(self.logfile)

        self.setUpRoot()
        args = [sys.executable,
                # XXX: 2010-04-26, Salgado, bug=570246: Deprecation warnings
                # in Twisted are not our problem.  They also aren't easy to
                # suppress, and cause test failures due to spurious stderr
                # output.  Just shut the whole bloody mess up.
                '-Wignore::DeprecationWarning',
                twistd_script, '-o', '-y', self.tacfile,
                '--pidfile', self.pidfile, '--logfile', self.logfile]
        if spew:
            args.append('--spew')
        if umask is not None:
            args.extend(('--umask', umask))

        # Run twistd, and raise an error if the return value is non-zero or
        # stdout/stderr are written to.
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        self.addCleanup(self.killTac)
        # XXX: JonathanLange 2008-03-19: This can raise EINTR. We should
        # really catch it and try again if that happens.
        stdout = proc.stdout.read()
        if stdout:
            raise TacException('Error running %s: unclean stdout/err: %s'
                               % (args, stdout))
        rv = proc.wait()
        if rv != 0:
            raise TacException('Error %d running %s' % (rv, args))

        self._waitForDaemonStartup()

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

    def _waitForDaemonStartup(self):
        """ Wait for the daemon to fully start.

        Times out after 20 seconds.  If that happens, the log file content
        will be included in the exception message for debugging purpose.

        :raises TacException: Timeout.
        """
        # Watch the log file for readyservice.LOG_MAGIC to signal that startup
        # has completed.
        now = time.time()
        deadline = now + 20
        while now < deadline and not self._hasDaemonStarted():
            time.sleep(0.1)
            now = time.time()

        if now >= deadline:
            raise TacException('Unable to start %s. Content of %s:\n%s' % (
                self.tacfile, self.logfile, open(self.logfile).read()))

    def tearDown(self):
        # For compatibility - migrate to cleanUp.
        self.cleanUp()

    def killTac(self):
        """Kill the TAC file if it is running."""
        pidfile = self.pidfile
        kill_by_pidfile(pidfile)

    def sendSignal(self, sig):
        """Send the given signal to the tac process."""
        pid = get_pid_from_file(self.pidfile)
        if pid is None:
            return
        os.kill(pid, sig)

    def setUpRoot(self):
        """Override this.

        This should be able to cope with the root already existing, because it
        will be left behind after each test in case it's needed to diagnose a
        test failure (e.g. log files might contain helpful tracebacks).
        """
        raise NotImplementedError

    @property
    def root(self):
        raise NotImplementedError

    @property
    def tacfile(self):
        raise NotImplementedError

    @property
    def pidfile(self):
        raise NotImplementedError

    @property
    def logfile(self):
        raise NotImplementedError
