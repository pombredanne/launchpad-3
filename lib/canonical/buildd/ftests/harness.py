# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import shutil

import canonical

from canonical.launchpad.daemons.tachandler import TacTestSetup

conffile = os.path.join(os.path.dirname(__file__), 'buildd-slave-test.conf')

class BuilddSlaveTestSetup(TacTestSetup):
    r"""Setup BuildSlave for use by functional tests

    >>> BuilddSlaveTestSetup().setUp()

    Make sure the server is running

    >>> import xmlrpclib
    >>> s = xmlrpclib.Server('http://localhost:8221/rpc/')
    >>> s.echo('Hello World')
    ['Hello World']
    >>> BuilddSlaveTestSetup().tearDown()

    Again for luck !
    
    >>> BuilddSlaveTestSetup().setUp()
    >>> s = xmlrpclib.Server('http://localhost:8221/rpc/')
    >>> s.echo('Hello World')
    ['Hello World']
    >>> BuilddSlaveTestSetup().tearDown()    
    """
    def setUpRoot(self):
        """Recreate empty root directory to avoid problems."""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.mkdir(self.root)
        filecache = os.path.join(self.root, 'filecache')
        os.mkdir(filecache)
        os.environ['BUILDD_SLAVE_CONFIG'] = conffile
        # XXX cprov 200505630
        # When we are about running it seriously we need :
        # * install sbuild package
        # * to copy the scripts for sbuild

    @property
    def root(self):
        return '/var/tmp/buildd'

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/buildd-slave.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'build-slave.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'build-slave.log')

