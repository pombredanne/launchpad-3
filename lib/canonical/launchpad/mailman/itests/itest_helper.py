# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Various helper functions and constants for use in test scripts."""

import os
import re
import sys
import time
import errno
import base64
import signal
import socket
import mailbox
import datetime
import tempfile

from email import message_from_file
from subprocess import Popen, PIPE

__all__ = [
    'HERE',
    'IntegrationTestFailure',
    'MAILMAN_BIN',
    'TOP',
    'create_transaction_manager',
    'make_browser',
    'num_requests_pending',
    'review_list',
    'run_mailman',
    'transactionmgr',
    ]

__metaclass__ = type


HERE = os.path.abspath(os.path.dirname(sys.argv[0]))
TOP = os.path.normpath(os.path.join(HERE, '../../../..'))
MAILMAN_BIN = os.path.normpath(os.path.join(
    os.path.dirname(sys.argv[0]), '../../../../', 'mailman', 'bin'))

LOG_GROWTH_WAIT_INTERVAL = datetime.timedelta(seconds=5)
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


class SMTPServer:
    """Start and manage an SMTP server subprocess.

    This server accepts messages from Mailman's outgoing queue runner just
    like a normal SMTP server.  However, this stores the messages in a Unix
    mbox file format so that they can be easily accessed for correctness.
    """
    def __init__(self):
        # Calculate a temporary file for the mbox.  This will be communicated
        # to the smtp2mbox subprocess when it gets started up.
        descriptor, mbox_filename = tempfile.mkstemp()
        os.close(descriptor)
        self._mbox_filename = mbox_filename
        self._pid = None

    def _command(self, command):
        """Send a command to the child process."""
        # Import this here since sys.path won't be set up properly when this
        # module is imported.
        from canonical.config import config
        s = socket.socket()
        s.connect(config.mailman.smtp)
        s.setblocking(0)
        s.send(command + '\r\n')
        s.close()

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
        while datetime.datetime.now() < until:
            try:
                self._command('QUIT')
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

    def reset(self):
        """Tell the child process to reset its mbox file."""
        self._command('RSET')

    def getMessages(self):
        """Return a list of all the messages currently in the mbox file."""
        # We have to use Python 2.4's icky mailbox module until Launchpad
        # upgrades Zope to a Python 2.5 compatible version.
        mbox = mailbox.UnixMailbox(
            open(self._mbox_filename), message_from_file)
        return list(mbox)

    def getMailboxSize(self):
        """Return the size in bytes of the mailbox."""
        return get_size(self._mbox_filename)


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
    """Watch a log file and wait until it has grown in size."""
    def __init__(self, log_file):
        # Import this here since sys.path isn't set up properly when this
        # module is imported.
        from Mailman.mm_cfg import LOG_DIR
        self._log_path = os.path.join(LOG_DIR, log_file)
        self._last_size = get_size(self._log_path)

    def wait(self):
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
    # Commit the change and wait until Mailman has actually created the
    # mailing list.  Don't worry about the return value because if the log
    # watcher times out, other things will notice this failure.
    serial_watcher = LogWatcher('serial')
    commit()
    # Wait until Mailman has actually created the mailing list.
    serial_watcher.wait()
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


def collect_archive_message_ids(team_name):
    """Collect all the X-Message-Id values in the team's archived messages."""
    from Mailman.mm_cfg import VAR_PREFIX
    mhonarc_path = os.path.join(VAR_PREFIX, 'mhonarc', 'itest-one')
    message_ids = []
    # Unfortunately, there's nothing we can wait on to know whether the
    # archiver has run yet or not, because the archive runner does not log
    # messages when it completes.
    archived_files = []
    for count in range(3):
        try:
            archived_files = [file_name
                              for file_name in os.listdir(mhonarc_path)
                              if file_name.endswith('.html')]
        except OSError, error:
            if error.errno != errno.ENOENT:
                raise
            # Sleep and try again.
        if len(archived_files) > 0:
            break
        time.sleep(0.5)
    for html_file in archived_files:
        file = open(os.path.join(mhonarc_path, html_file))
        try:
            data = file.read()
        finally:
            file.close()
        for line in data.splitlines():
            if line.startswith('<!DOCTYPE'):
                break
            mo = re.match('<!--X-Message-Id:\s*(?P<id>[\S]+)', line, re.I)
            if mo:
                message_ids.append(mo.group('id'))
                break
    return message_ids


def num_requests_pending(list_name):
    """Return the number of requests pending for the list.

    We do it this way in order to be totally safe, so that there's no
    possibility of leaving a locked list floating around.  doctest doesn't
    always do the right thing.
    """
    # Import this here because paths aren't set up correctly in the module
    # globals.
    from Mailman.MailList import MailList
    # The list must be locked to make this query.
    mailing_list = MailList(list_name)
    try:
        return mailing_list.NumRequestsPending()
    finally:
        mailing_list.Unlock()
