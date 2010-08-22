# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import with_statement

"""Test harness for TAC (Twisted Application Configuration) files."""

__metaclass__ = type

__all__ = [
    'TacTestSetup',
    'ReadyService',
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

from twisted.application import service
from twisted.python import log

# This file is used by launchpad-buildd, so it cannot import any
# Launchpad code!

def two_stage_kill(pid, poll_interval=0.1, num_polls=50):
    """Kill process 'pid' with SIGTERM. If it doesn't die, SIGKILL it.

    :param pid: The pid of the process to kill.
    :param poll_interval: The polling interval used to check if the
        process is still around.
    :param num_polls: The number of polls to do before doing a SIGKILL.
    """
    # Kill the process.
    try:
        os.kill(pid, SIGTERM)
    except OSError, e:
        if e.errno in (errno.ESRCH, errno.ECHILD):
            # Process has already been killed.
            return

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
    try:
        os.kill(pid, SIGKILL)
    except OSError:
        # Already terminated
        pass


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

LOG_MAGIC = 'daemon ready!'


class TacException(Exception):
    """Error raised by TacTestSetup."""


class TacTestSetup:
    """Setup an TAC file as daemon for use by functional tests.

    You can override setUpRoot to set up a root directory for the daemon.
    """

    def setUp(self, spew=False, umask=None):
        # Before we run, we want to make sure that we have cleaned up any
        # previous runs. Although tearDown() should have been called already,
        # we can't guarantee it.
        self.tearDown()

        # setUp() watches the logfile to determine when the daemon has fully
        # started. If it sees an old logfile, then it will find the LOG_MAGIC
        # string and return immediately, provoking hard-to-diagnose race
        # conditions. Delete the logfile to make sure this does not happen.
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

        Startup is recognized by the appearance of LOG_MAGIC in the log
        file.
        """
        if os.path.exists(self.logfile):
            with open(self.logfile, 'r') as logfile:
                return LOG_MAGIC in logfile.read()
        else:
            return False

    def _waitForDaemonStartup(self):
        """ Wait for the daemon to fully start.

        Times out after 20 seconds.  If that happens, the log file content
        will be included in the exception message for debugging purpose.

        :raises TacException: Timeout.
        """
        # Watch the log file for LOG_MAGIC to signal that startup has
        # completed.
        now = time.time()
        deadline = now + 20
        while now < deadline and not self._hasDaemonStarted():
            time.sleep(0.1)
            now = time.time()

        if now >= deadline:
            raise TacException('Unable to start %s. Content of %s:\n%s' % (
                self.tacfile, self.logfile, open(self.logfile).read()))

    def tearDown(self):
        self.killTac()

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


class ReadyService(service.Service):
    """Service that logs a 'ready!' message once the reactor has started."""

    def startService(self):
        from twisted.internet import reactor
        reactor.addSystemEventTrigger('after', 'startup', log.msg, LOG_MAGIC)
        service.Service.startService(self)
