# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile
import os
import shutil
import gc
import stat

from bzrlib.bzrdir import ScratchDir
import bzrlib.branch
from bzrlib.tests import TestCase as BzrTestCase
from bzrlib.errors import NoSuchFile, NotBranchError, PermissionDenied
from bzrlib.transport import get_transport
from bzrlib.transport import sftp
from bzrlib.tests import TestCase as BzrTestCase

from twisted.python.util import sibpath

from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.supermirrorsftp.tests.test_acceptance import (
    SFTPSetup, SFTPTestCase)
from canonical.authserver.ftests.harness import AuthserverTacTestSetup


class SFTPTests(SFTPTestCase):

    def test_rmdir_branch(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = get_transport(self.server_base + '~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Remove a directory.
        # XXX Andrew Bennetts 2006-06-23:
        #    bzrlib currently throws an IOError with no way to distinguish
        #    "permission denied" errors from other kinds.  When we upgrade
        #    Twisted, bzrlib will receive more useful errors and throw
        #    PermissionDenied here instead.  We catch both here so we pass with
        #    either version of Twisted.
        self.assertRaises((PermissionDenied, IOError), transport.rmdir, 'foo')


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
