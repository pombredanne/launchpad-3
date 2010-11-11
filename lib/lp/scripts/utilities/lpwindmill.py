# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Windmill test integration wrapper for Launchpad.

This wrapper starts a test Launchpad instance that can be
used by Windmill.

If the --server-only option is given, only the Launchpad server
is started.  This allows one to invoke the windmill script multiple
time directly.
"""

import atexit
import sys
import time

import windmill.bin.windmill_bin

from canonical.config import config
from canonical.testing.layers import (
    BaseLayer,
    DatabaseLayer,
    GoogleServiceLayer,
    LayerProcessController,
    LibrarianLayer,
    )


def runLaunchpad():
    """Set-up the Launchpad app-server against which windmill tests are run.
    """
    config.setInstance('testrunner-appserver')
    # Hard-code the app-server configuration, since that's what can
    # work with windmill.
    sys.stderr.write('Starting up Launchpad... ')
    BaseLayer.setUp()
    DatabaseLayer.setUp()
    # The below tests installs atexit handler that will clean-up their
    # resources on. So we install only one for the Database.
    atexit.register(DatabaseLayer.tearDown)
    LibrarianLayer.setUp()
    GoogleServiceLayer.setUp()
    LayerProcessController._setConfig()
    LayerProcessController.startSMTPServer()
    LayerProcessController.startAppServer()
    sys.stderr.write('done.\n')


def runWindmill():
    """Start windmill using our command line arguments.

    This function exits once windmill has terminated.
    """
    # The windmill main function will interpret the command-line arguments
    # for us.
    windmill.bin.windmill_bin.main()


def waitForInterrupt():
    """Sits in a sleep loop waiting for a Ctrl-C."""
    try:
        sys.stderr.write('Waiting for Ctrl-C...\n')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pass


def main():
    runLaunchpad()
    if sys.argv[1] == '--server-only':
        waitForInterrupt()
    else:
        runWindmill()
    sys.stderr.write('Shutting down Launchpad...\n')
