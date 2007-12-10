# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Various helper functions and constants for use in test scripts."""

import os
import sys
import time
import errno
import base64
import signal
import socket
import mailbox
import datetime

from email import message_from_file
from subprocess import Popen, PIPE

__all__ = [
    'HERE',
    'IntegrationTestFailure',
    'MAILMAN_BIN',
    'TOP',
    'create_transaction_manager',
    'make_browser',
    'mbox_iterator'
    'review_list',
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
LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=30)
SECONDS_TO_SNOOZE = 0.1


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


def wait_for_mailman():
    """Wait for Mailman to Do Something based on an XMLRPC response."""
    # Import this here because sys.path won't be set up properly when this
    # module is imported.
    from Mailman import mm_cfg
    # This starts by getting the mtime of Mailman's logs/xmlrpc file.  Then it
    # waits until this file has changed, indicating that Mailman has processed
    # the last request.
    #
    # It's actually more complicated than that due to a race condition.
    # Mailman might be updating as we're committing the transaction, and the
    # first log growth we see may not be about the change we're interested in.
    # This occurs because we can't atomically get the mtime and commit the
    # database change that will trigger a Mailman update.
    #
    # To solve this, we actually wait through two cycles of log growth.
    # Mailman's XMLRPCRunner will always print a message to its log file when
    # it talks to Launchpad, so two cycles ensures that the operaton triggered
    # by the transaction commit has actually been handled.
    log_file = os.path.join(mm_cfg.LOG_DIR, 'xmlrpc')
    last_mtime = os.stat(log_file).st_mtime
    until = datetime.datetime.now() + LOG_GROWTH_WAIT_INTERVAL
    cycle = 0
    while True:
        if os.stat(log_file).st_mtime > last_mtime:
            cycle += 1
            if cycle >= MAX_CYCLES:
                # We want no output in the doctest for the expected success.
                return None
        if datetime.datetime.now() > until:
            return 'Timed out'
        time.sleep(SECONDS_TO_SNOOZE)


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


def get_size(path):
    """Return the size of a file, or -1 if it doesn't exist."""
    try:
        return os.stat(path).st_size
    except OSError, error:
        if error.errno == errno.ENOENT:
            # Return -1 when the file does not exist, so it always
            # compares less than an existing but empty file.
            return -1
        # Some other error occurred.
        raise


class LogWatcher:
    """Watch a log file and wait until it has grown in size.

    Use this instead of wait_for_mailman() when watching a log file that isn't
    guaranteed to grow or even exist (such as logs/vette).
    """
    def __init__(self, log_file):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        from Mailman.mm_cfg import LOG_DIR
        self._log_path = os.path.join(LOG_DIR, log_file)
        self._last_size = get_size(self._log_path)

    def wait_for_growth(self):
        """Wait for a while, or until the file has grown."""
        until = datetime.datetime.now() + LOG_GROWTH_WAIT_INTERVAL
        while True:
            size = get_size(self._log_path)
            if size > self._last_size:
                # Return None on success for doctest convenience.
                self._last_size = size
                return None
            if datetime.datetime.now() > until:
                return 'Timed out'
            time.sleep(SECONDS_TO_SNOOZE)

    def resync(self):
        """Re-sync the file size so that we can watch it again."""
        self._last_size = get_size(self._log_path)


def mbox_iterator(mbox_filename):
    """Iterate over the messages in a mailbox."""
    # We have to use Python 2.4's icky mailbox module until Launchpad upgrades
    # Zope to a Python 2.5 compatible version.
    mbox = mailbox.UnixMailbox(open(mbox_filename), message_from_file)
    for message in mbox:
        yield message


def review_list(list_name, status=None):
    """Helper for approving a mailing list.

    This functionality is not yet exposed through the web.
    """
    # These imports are at file scope because the paths are not yet set up
    # correctly when this module is imported.
    from canonical.database.sqlbase import commit
    from canonical.launchpad.ftests import login, logout, mailinglists_helper
    from canonical.launchpad.interfaces import IMailingListSet
    from zope.component import getUtility
    login('foo.bar@canonical.com')
    mailinglists_helper.review_list(list_name, status)
    commit()
    # Wait until Mailman has actually created the mailing list.
    wait_for_mailman()
    # Return an updated mailing list object.
    mailing_list = getUtility(IMailingListSet).get(list_name)
    logout()
    return mailing_list


def beta_program_enable(team_name):
    """Helper for joining the mailing list beta program.

    This is a pure convenience function, which can go away when mailing lists
    go public.
    """
    # These imports are at file scope because the paths are not yet set up
    # correctly when this module is imported.
    from canonical.database.sqlbase import commit
    from canonical.launchpad.ftests import mailinglists_helper
    mailinglists_helper.beta_program_enable(team_name)
    commit()
