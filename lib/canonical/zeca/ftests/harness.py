# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys, os, os.path, shutil, time
from signal import SIGTERM
from canonical.config import config
import canonical

keysdir = os.path.join(os.path.dirname(__file__), 'keys')

class ZecaTestSetup(object):
    r"""Setup a zeca for use by functional tests
    
    >>> from urllib import urlopen
    >>> host = config.gpghandler.host
    >>> port = config.gpghandler.port

    >>> ZecaTestSetup().setUp()

    Make sure the server is running

    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'

    >>> ZecaTestSetup().tearDown()
    
    And again for luck

    >>> ZecaTestSetup().setUp()
    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'
    >>> ZecaTestSetup().tearDown()
    """
    def setUp(self, spew=False):
        self._kill()
        # ensure the access to root
        self.setupRoot()

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
                raise RuntimeError, 'Unable to start Zeca'
            time.sleep(0.1)

    def tearDown(self):
        self._kill()

    def _kill(self):
        """Kill the Zeca, if it is running, and clean up any mess"""
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

    def setupRoot(self):
        """Recreate root directory and copy needed keys"""
        if os.access(self.root, os.F_OK):
            shutil.rmtree(self.root)
        shutil.copytree(keysdir, self.root)
        
    def root(self):
        return config.zeca.root
    root = property(root)

    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/zeca.tac'
            ))
    tacfile = property(tacfile)

    def pidfile(self):
        return os.path.join(self.root, 'zeca.pid')
    pidfile = property(pidfile)

    def logfile(self):
        return os.path.join(self.root, 'zeca.log')
    logfile = property(logfile)

    def spewbucket(self):
        return os.path.join(self.root, 'spew.log')
    spewbucket = property(spewbucket)

