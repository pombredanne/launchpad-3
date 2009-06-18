# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Windmill test integration wrapper for Launchpad.

This wrapper starts a test Launchpad instance that can be
used by Windmill.

If the --server-only option is given, only the Launchpad server
is started.  This allows one to invoke the windmill script multiple
time directly.
"""

import os
import sys
import time

here = os.path.dirname(os.path.realpath(__file__))

import atexit
import signal
import subprocess
from canonical.config import config
from canonical.testing.layers import (
    BaseLayer,
    DatabaseLayer,
    LibrarianLayer,
    GoogleServiceLayer,
    LayerProcessController)

def setUpLaunchpad():
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
    LayerProcessController.startSMTPServer()
    LayerProcessController.startAppServer()
    sys.stderr.write('done.\n')


def runWindmill():
    """Start windmill using our command line arguments.

    This function exits once windmill has terminated.
    """
    windmill_cmdline = [
        os.path.join(
            here, os.pardir, os.pardir, os.pardir, os.pardir, 
            'bin', 'windmill'),
        ]
    windmill_cmdline.extend(sys.argv[1:])
    windmill = subprocess.Popen(windmill_cmdline, close_fds=True)
    try:
        windmill.wait()
    except KeyboardInterrupt:
        os.kill(windmill.pid, signal.SIGTERM)


def waitForInterrupt():
    """Sits in a sleep loop waiting for a Ctrl-C."""
    try:
        sys.stderr.write('Waiting for Ctrl-C...\n')
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        pass


def main():
    setUpLaunchpad()
    if sys.argv[1] == '--server-only':
        waitForInterrupt()
    else:
        runWindmill()
    sys.stderr.write('Shutting down Launchpad...\n')
