#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
"""Windmill test integration wrapper for Launchpad.

This wrapper starts a test Launchpad instance that can be
used by Windmill.
"""

import os
import sys

# Fix-up our path so that we can find all the modules.
here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(here, 'lib'))
sys.path.insert(0, os.path.join(here, 'lib', 'mailman'))

original_environ = dict(os.environ)
# Set the path for spawned process.
os.environ['PYTHONPATH'] = ":".join(sys.path)

# Hard-code the app-server configuration, since that's what can
# work with windmill.
os.environ['LPCONFIG'] = 'testrunner-appserver'

import atexit
import signal
import subprocess
from canonical.testing.layers import (
    BaseLayer,
    DatabaseLayer,
    LibrarianLayer,
    GoogleServiceLayer,
    LayerProcessController)

def setUpLaunchpad():
    """Set-up the Launchpad app-server against which windmill tests are run.
    """
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

if __name__ == '__main__':
    setUpLaunchpad()
    windmill_cmdline = [
        os.path.join(here, 'utilities', 'windmill.py'),
        ]
    windmill_cmdline.extend(sys.argv[1:])
    windmill = subprocess.Popen(
        windmill_cmdline, close_fds=True, env=original_environ)
    try:
        windmill.wait()
    except KeyboardInterrupt:
        os.kill(windmill.pid, signal.SIGTERM)
    sys.stderr.write('Shutting down Launchpad...\n')
