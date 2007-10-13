# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Various helper functions and constants for use in test scripts."""

import os
import sys
import base64
import datetime

from subprocess import Popen, PIPE


HERE = os.path.abspath(os.path.dirname(sys.argv[0]))
TOP = os.path.normpath(os.path.join(HERE, '../../../..'))
MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))

XMLRPC_URL = 'http://xmlrpc.launchpad.dev:8087/mailinglists'


class IntegrationTestFailure(Exception):
    """An integration test failed."""


class IntegrationTestTimeout(Exception):
    """A timeout occurred without getting expected output."""


def auth(user, password):
    """Create a Base64 encoded Basic Auth string."""
    return 'Basic ' + base64.encodestring('%s:%s' % (user, password))


def poll(function):
    """Standard loop for checking something for a while."""
    # Now wait a little while for Mailman to do some operation.  Using the
    # default Mailman polling frequency, the list should get created in under
    # 20 seconds.
    until = datetime.datetime.now() + datetime.timedelta(seconds=20)
    while datetime.datetime.now() < until:
        if function():
            return
    raise IntegrationTestTimeout('Timed out before success')


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
    # Set up the connection to the database.  We use the 'testadmin' uses
    # because it has rights to do nasty things like delete Person entries.
    transactionmgr = initZopeless(dbuser='testadmin')


def make_browser():
    # Import this here because our paths are not set up correctly in the
    # global module scope.  This is like the setupBrowser for page tests, but
    # with the base64 hack needed for authentication from the outside.
    from zope.testbrowser.browser import Browser
    browser = Browser()
    browser.handleErrors = False
    browser.addHeader('Authorization', auth('no-priv@canonical.com', 'test'))
    return browser
