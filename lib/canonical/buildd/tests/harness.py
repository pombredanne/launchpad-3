# Copyright 2004-2008 Canonical Ltd.  All rights reserved.


__metaclass__ = type
__all__ = [
    'BuildlogSecurityTests',
    'BuilddTestCase',
    ]

import os
import shutil
import tempfile
import unittest
from ConfigParser import SafeConfigParser

import canonical

from canonical.buildd.slave import BuildDSlave
from canonical.launchpad.daemons.tachandler import TacTestSetup


test_conffile = os.path.join(
    os.path.dirname(__file__), 'buildd-slave-test.conf')


class MockBuildManager(object):
    """Mock BuildManager class.

    Only implements 'is_archive_private' as False.
    """
    is_archive_private = False


class BuilddTestCase(unittest.TestCase):
    """Unit tests for logtail mechanisms."""

    def setUp(self):
        """Setup a BuildDSlave using the test config."""
        conf = SafeConfigParser()
        conf.read(test_conffile)
        conf.set("slave", "filecache", tempfile.mkdtemp())

        self.slave = BuildDSlave(conf)
        self.slave._log = True
        self.slave.manager = MockBuildManager()

        self.here = os.path.abspath(os.path.dirname(__file__))

    def tearDown(self):
        """Remove the 'filecache' directory used for the tests."""
        if os.path.isdir(self.slave._cachepath):
            shutil.rmtree(self.slave._cachepath)

    def makeLog(self, size):
        """Inject data into the default buildlog file."""
        f = open(self.slave.cachePath('buildlog'), 'w')
        f.write("x" * size)
        f.close()


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

    >>> s.info()
    ['1.0', 'i386', ['debian']]

    >>> s.status()
    ['BuilderStatus.IDLE', '']

    >>> BuilddSlaveTestSetup().tearDown()
    """
    def setUpRoot(self):
        """Recreate empty root directory to avoid problems."""
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.mkdir(self.root)
        filecache = os.path.join(self.root, 'filecache')
        os.mkdir(filecache)
        os.environ['HOME'] = self.root
        os.environ['BUILDD_SLAVE_CONFIG'] = test_conffile
        # XXX cprov 2005-05-30:
        # When we are about running it seriously we need :
        # * install sbuild package
        # * to copy the scripts for sbuild

    def tearDown(self):
        """Tear down the system normally and additionaly remove the root."""
        TacTestSetup.tearDown(self)
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)

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

