"""Test harness for TAC (Twisted Application Configuration) files.
"""
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TacTestSetup', 'ReadyService', 'TacException']

import sys
import os
import time
from signal import SIGTERM
import subprocess

from twisted.application import service
from twisted.python import log


LOG_MAGIC = 'daemon ready!'

class TacException(Exception):
    """Error raised by TacTestSetup."""


class TacTestSetup:
    """Setup an TAC file as daemon for use by functional tests.

    You can override setUpRoot to set up a root directory for the daemon.
    """
    def setUp(self, spew=False):
        self.killTac()
        self.setUpRoot()
        ver = sys.version[:3]
        args = ['twistd' + ver, '-o', '-y', self.tacfile, '--pidfile',
                self.pidfile, '--logfile', self.logfile]
        if spew:
            args.append('--spew')

        # Run twistd, and raise an error if the return value is non-zero or
        # stdout/stderr are written to.
        proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        stdout = proc.stdout.read()
        if stdout:
            raise TacException('Error running %s: unclean stdout/err: %s' 
                               % (args, stdout))
        rv = proc.wait()
        if rv != 0:
            raise TacException('Error %d running %s' % (rv, args))

        # Wait for the daemon to fully start (as determined by watching the log
        # file).  If it takes more than 10 seconds, we assume it's gone wrong,
        # and raise TacException.
        start = time.time()
        while True:
            if time.time() > start + 10:
                raise TacException('Unable to start %s' % (self.tacfile,))
            if os.path.exists(self.logfile):
                if LOG_MAGIC in open(self.logfile, 'r').read():
                    break
            time.sleep(0.1)

    def tearDown(self):
        self.killTac()

    def killTac(self):
        """Kill the TAC file, if it is running, and clean up any mess"""
        pidfile = self.pidfile
        if os.path.exists(pidfile):
            pid = open(pidfile,'r').read().strip()
            # Keep killing until it is dead
            while True:
                try:
                    os.kill(int(pid), SIGTERM)
                    time.sleep(0.1)
                except OSError:
                    break

    def setUpRoot(self):
        """Override this.

        This should be able to cope with the root already existing, because it
        will be left behind after each test in case it's needed to diagnose a
        test failure (e.g. log files might contain helpful tracebacks).
        """
        raise NotImplementedError

    # XXX cprov 20050708
    # We don't really need those information as property,
    # they can be implmented as simple attributes since they
    # store static information. Sort it out soon.

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

