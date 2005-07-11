# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = ['TacTestSetup']

import sys, os, os.path, shutil, time
from signal import SIGTERM
import canonical

class TacTestSetup(object):
    r"""Setup an TAC file as daemon for use by functional tests."""
    def setUp(self, spew=False):
        self.killTac()
        self.setUpRoot()
        ver = sys.version[:3]
        cmd = 'twistd%s -o -y %s --pidfile %s --logfile %s' % (
                ver, self.tacfile, self.pidfile, self.logfile
                )
        if spew:
            cmd = cmd + ' --spew > %s' % self.spewbucket
        rv = os.system(cmd)
        if rv != 0:
            raise RuntimeError, 'Error %d running %s' % (rv, cmd)

        start = time.time()
        while 1:
            if not os.path.exists(self.logfile):
                continue
            if 'set uid/gid' in open(self.logfile, 'r').read():
                break
            if time.time() > start + 10:
                raise RuntimeError, 'Unable to start Librarian'
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
            self.tearDownRoot()
        
    def setUpRoot(self):
        raise NotImplementedError

    def tearDownRoot(self):
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

    @property
    def spewbucket(self):
        raise NotImplementedError
