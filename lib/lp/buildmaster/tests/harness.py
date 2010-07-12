# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""TacHandler for `buildd-manager` daemon."""

__metaclass__ = type

__all__ = [
    'BuilddManagerTestSetup',
    ]


import os

import canonical
from canonical.launchpad.daemons.tachandler import TacTestSetup

from lp.services.osutils import remove_tree


class BuilddManagerTestSetup(TacTestSetup):
    """Setup BuilddManager for use by functional tests."""

    def setUpRoot(self):
        """Create `TacTestSetup.root` for storing the log and pid files.

        Remove the directory and create a new one if it exists.
        """
        remove_tree(self.root)
        os.makedirs(self.root)

    @property
    def root(self):
        """Directory where log and pid files will be stored."""
        return '/var/tmp/buildd-manager/'

    @property
    def tacfile(self):
        """Absolute path to the 'buildd-manager' tac file."""
        return os.path.abspath(os.path.join(
            os.path.dirname(canonical.__file__), os.pardir, os.pardir,
            'daemons/buildd-manager.tac'
            ))

    @property
    def pidfile(self):
        """The tac pid file path.

        Will be created when the tac file actually runs.
        """
        return os.path.join(self.root, 'buildd-manager.pid')

    @property
    def logfile(self):
        """The tac log file path.

        Will be created when the tac file actually runs.
        """
        return os.path.join(self.root, 'buildd-manager.log')
