"""Test harness for TAC (Twisted Application Configuration) files.
"""
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TacTestSetup']

import sys, os, os.path, shutil, time
from signal import SIGTERM

from twisted.application import service
from twisted.python import log


LOG_MAGIC = 'daemon ready!'


class TacTestSetup:
    """Setup an TAC file as daemon for use by functional tests.
    
    You can override setUpRoot to set up a root directory for the daemon.
    """
    def setUp(self, spew=False):
        self.killTac()
        self.setUpRoot()
        ver = sys.version[:3]
        cmd = 'twistd%s -o -y %s --pidfile %s --logfile %s' % (
                ver, self.tacfile, self.pidfile, self.logfile
                )
        if spew:
            cmd = cmd + ' --spew'
        rv = os.system(cmd)
        if rv != 0:
            raise RuntimeError, 'Error %d running %s' % (rv, cmd)

        start = time.time()
        while 1:
            if not os.path.exists(self.logfile):
                continue
            if LOG_MAGIC in open(self.logfile, 'r').read():
                break
            if time.time() > start + 10:
                raise RuntimeError('Unable to start %s' % self.tacfile)
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
            

