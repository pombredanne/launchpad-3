# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile
import os
import shutil
import gc
import stat
import sys
import traceback

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

    # XXX: AndrewBennetts 2006-06-07:
    # failUnlessRaises from twisted/trial/unittest.py (MIT licensed), unlike
    # pyunit's failUnlessRaises it returns the caught exception, making it
    # possible to assert things about the attributes of the exception, not just
    # the type of the exception.
    def failUnlessRaises(self, exception, f, *args, **kwargs):
        """fails the test unless calling the function C{f} with the given C{args}
        and C{kwargs} does not raise C{exception}. The failure will report the
        traceback and call stack of the unexpected exception.
        
        @param exception: exception type that is to be expected
        @param f: the function to call
    
        @return: The raised exception instance, if it is of the given type.
        @raise self.failureException: Raised if the function call does not raise
            an exception or if it raises an exception of a different type.
        """
        try:
            result = f(*args, **kwargs)
        except exception, inst:
            return inst
        except:
            raise self.failureException('%s raised instead of %s:\n %s'
                                        % (sys.exc_info()[0],
                                           exception.__name__,
                                           ''.join(traceback.format_stack())))
        else:
            raise self.failureException('%s not raised (%r returned)'
                                        % (exception.__name__, result))
    assertRaises = failUnlessRaises

    def test_rmdir_branch(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = get_transport(self.server_base + '~testuser/+junk')
        transport.mkdir('foo')
        transport.mkdir('bar')
        self.failUnless(stat.S_ISDIR(transport.stat('foo').st_mode))
        self.failUnless(stat.S_ISDIR(transport.stat('bar').st_mode))

        # Remove a directory.
        e = self.assertRaises(PermissionDenied, transport.rmdir, 'foo')
        self.failUnless(
            "removing branch directory 'foo' is not allowed." in e.extra)

    def test_mkdir_toplevel_error(self):
        # You cannot create a top-level directory.
        transport = get_transport(self.server_base)
        e = self.assertRaises(PermissionDenied, transport.mkdir, 'foo')
        self.failUnless(
            "Branches must be inside a person or team directory." in e.extra,
            e.extra)

    def test_mkdir_invalid_product_error(self):
        # Make some directories under ~testuser/+junk (i.e. create some empty
        # branches)
        transport = get_transport(self.server_base + '~testuser')

        # You cannot create a product directory unless the product name is
        # registered in Launchpad.
        e = self.assertRaises(PermissionDenied, 
                transport.mkdir, 'no-such-product')
        self.failUnless(
            "Directories directly under a user directory must be named after a "
            "product name registered in Launchpad" in e.extra,
            e.extra)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
