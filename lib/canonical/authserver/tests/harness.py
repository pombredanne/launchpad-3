# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import unittest
import os
import shutil

from twisted.python.util import sibpath

import canonical
from canonical.launchpad.daemons.tachandler import TacTestSetup


class AuthserverTacTestSetup(TacTestSetup):
    root = '/tmp/authserver-test'

    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/authserver.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'authserver.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'authserver.log')
