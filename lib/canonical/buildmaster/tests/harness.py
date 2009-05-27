# Copyright 2009 Canonical Ltd.  All rights reserved.
"""TacHandler for `buildd-manager` daemon."""

__metaclass__ = type

__all__ = [
    'BuilddManagerTestSetup',
    ]


import os
import shutil

import canonical
from canonical.launchpad.daemons.tachandler import TacTestSetup


class BuilddManagerTestSetup(TacTestSetup):
    """Setup BuilddManager for use by functional tests."""

    def setUpRoot(self):
        if os.path.exists(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root)

    @property
    def root(self):
        return '/var/tmp/buildd-manager/'

    @property
    def tacfile(self):
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/buildd-manager.tac'
            ))

    @property
    def pidfile(self):
        return os.path.join(self.root, 'buildd-manager.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'buildd-manager.log')
