# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys, os, os.path, shutil, time
from signal import SIGTERM
from canonical.config import config
import canonical

class LibrarianTestSetup(object):
    r"""Setup a librarian for use by functional tests
    
    >>> from urllib import urlopen
    >>> from canonical.config import config
    >>> host = config.librarian.download_host
    >>> port = config.librarian.download_port

    >>> LibrarianTestSetup().setUp()

    Make sure the server is running

    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'

    >>> LibrarianTestSetup().tearDown()
    
    And again for luck

    >>> LibrarianTestSetup().setUp()
    >>> urlopen('http://%s:%d/' % (host, port)).readline()
    'Copyright 2004-2005 Canonical Ltd.\n'
    >>> LibrarianTestSetup().tearDown()

    """
    def setUp(self, spew=False):
        self._kill()
        os.makedirs(self.root, 0700)
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
        self._kill()

    def _kill(self):
        """Kill the Librarian, if it is running, and clean up any mess"""
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
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
 
    def root(self):
        return config.librarian.server.root
    root = property(root)

    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/librarian.tac'
            ))
    tacfile = property(tacfile)

    def pidfile(self):
        return os.path.join(self.root, 'librarian.pid')
    pidfile = property(pidfile)

    def logfile(self):
        return os.path.join(self.root, 'librarian.log')
    logfile = property(logfile)

    def spewbucket(self):
        return os.path.join(self.root, 'spew.log')
    spewbucket = property(spewbucket)

# Kill any librarian left lying around from a previous interrupted run.
# Be paranoid since we trash the librarian directory as part of this.
assert config.default_section == 'testrunner', \
        'Imported dangerous test harness outside of the test runner'
LibrarianTestSetup()._kill()
