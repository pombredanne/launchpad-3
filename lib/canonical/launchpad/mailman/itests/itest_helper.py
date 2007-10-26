# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Various helper functions and constants for use in test scripts."""

import os
import sys
import time
import errno
import base64
import signal
import socket
import datetime

from subprocess import Popen, PIPE

__all__ = [
    'HERE',
    'IntegrationTestFailure',
    'MAILMAN_BIN',
    'TOP',
    'create_transaction_manager',
    'make_browser',
    'run_mailman',
    'transactionmgr',
    'wait_for_mailman',
    ]

__metaclass__ = type


HERE = os.path.abspath(os.path.dirname(sys.argv[0]))
TOP = os.path.normpath(os.path.join(HERE, '../../../..'))
MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))

MAX_CYCLES = 2


class IntegrationTestFailure(Exception):
    """An error occurred in the integration test framework."""


def auth(user, password):
    """Create a Base64 encoded Basic Auth string."""
    return 'Basic ' + base64.encodestring('%s:%s' % (user, password))


def run_mailman(*args):
    """Run a Mailman script."""
    proc = Popen(args, stdout=PIPE, stderr=PIPE, cwd=MAILMAN_BIN)
    stdout, stderr = proc.communicate()
    if stderr:
        raise IntegrationTestFailure(stderr)
    return stdout


transactionmgr = None
def create_transaction_manager():
    """Create the global transaction manager for this side of the tests."""
    global transactionmgr
    # Import this here because our paths are not set up correctly in the
    # global module scope.
    from canonical.lp import initZopeless
    # Set up the connection to the database.  We use the 'testadmin' user
    # because it has rights to do nasty things like delete Person entries.
    transactionmgr = initZopeless(dbuser='testadmin')


def make_browser():
    """Create and return an authorized browser."""
    # Import this here because our paths are not set up correctly in the
    # global module scope.  This is like the setupBrowser for page tests, but
    # with the base64 hack needed for authentication from the outside.
    from zope.testbrowser.browser import Browser
    browser = Browser()
    browser.handleErrors = False
    browser.addHeader('Authorization', auth('no-priv@canonical.com', 'test'))
    return browser


def wait_for_mailman(log_name='xmlrpc'):
    """Wait for Mailman to Do Something based on an XMLRPC response."""
    # Import this here because sys.path won't be set up properly when this
    # module is imported.
    from Mailman import mm_cfg
    # This starts by getting the mtime of Mailman's logs/xmlrpc file.  Then it
    # waits until this file has changed, indicating that Mailman has processed
    # the last request.
    #
    # It's actually more complicated than that due to race conditions.
    # Because we can't atomically get the mtime and apply the database change
    # that will trigger a Mailman update, we actually wait through two cycles
    # of changes.  Mailman's XMLRPCRunner will always print a message to its
    # log file when it talks to Launchpad, so two cycles ensures that the
    # operaton triggered by the transaction commit has actually been handled.
    log_file = os.path.join(mm_cfg.LOG_DIR, log_name)
    last_mtime = os.stat(log_file).st_mtime
    until = datetime.datetime.now() + datetime.timedelta(seconds=30)
    cycle = 0
    while True:
        if os.stat(log_file).st_mtime > last_mtime:
            cycle += 1
            if cycle >= MAX_CYCLES:
                # We want no output in the doctest for the expected success.
                return None
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(0.1)


class SMTPServer:
    """Start and manage an SMTP server subprocess.

    This server accepts messages from Mailman's outgoing queue runner just
    like a normal SMTP server.  However, this stores the messages in a Unix
    mbox file format so that they can be easily accessed for correctness.
    """
    def __init__(self, mbox_filename):
        self._mbox_filename = mbox_filename
        self._pid = None

    def start(self):
        """Fork and exec the child process."""
        self._pid = pid = os.fork()
        if pid == 0:
            # Child -- exec the server
            server_path = os.path.join(HERE, 'smtp2mbox')
            os.execl(sys.executable, sys.executable, server_path,
                     self._mbox_filename)
            # We should never get here!
            os._exit(1)
        # Parent -- wait until the child is listening.
        until = datetime.datetime.now() + datetime.timedelta(seconds=10)
        s = socket.socket()
        # Import this here since sys.path won't be set up properly when this
        # module is imported.
        from canonical.config import config
        while datetime.datetime.now() < until:
            try:
                s.connect(config.mailman.smtp)
                s.setblocking(0)
                s.send('QUIT\r\n')
                s.close()
                # Return None for no output in the doctest.
                return None
            except socket.error:
                time.sleep(0.5)
        print 'No SMTP server listening'

    def stop(self):
        """Stop the child process."""
        os.kill(self._pid, signal.SIGTERM)
        os.waitpid(self._pid, 0)
        try:
            os.remove(self._mbox_filename)
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise
