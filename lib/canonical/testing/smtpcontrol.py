# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A child SMTP server for Mailman testing."""

__metaclass__ = type
__all__ = [
    'SMTPControl',
    ]


import os
import sys
import time
import errno
import signal
import socket
import mailbox
import datetime
import tempfile

from email import message_from_file
from lazr.config import as_host_port

from canonical.config import config
from canonical.testing import smtp2mbox


class SMTPControl:
    """Start and manage an SMTP server subprocess.

    This server accepts messages from Mailman's outgoing queue runner just
    like a normal SMTP server.  However, this stores the messages in a Unix
    mbox file format so that they can be easily accessed for correctness.
    """
    def __init__(self):
        # Create a temporary file for the mbox.  This will be communicated
        # to the smtp2mbox subprocess when it gets started up.
        descriptor, mbox_filename = tempfile.mkstemp()
        os.close(descriptor)
        self._mbox_filename = mbox_filename
        self._pid = None

    def _command(self, command):
        """Send a command to the child process."""
        s = socket.socket()
        s.connect(as_host_port(config.mailman.smtp))
        s.setblocking(0)
        s.send(command + '\r\n')
        s.close()

    def start(self):
        """Fork and exec the child process."""
        import Mailman
        self._pid = pid = os.fork()
        if pid == 0:
            # Child -- exec the server
            host, port = as_host_port(config.mailman.smtp)
            logfile = os.path.join(
                config.mailman.build_var_dir, 'logs', 'smtpd')
            os.execl(sys.executable, sys.executable,
                     smtp2mbox.__file__,
                     '--host', host, '--port', str(port),
                     '--mbox', self._mbox_filename,
                     '--path', os.path.dirname(Mailman.__file__),
                     '--logfile', logfile,
                     )
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

    def getMessages(self, reset=True):
        """Return a list of all the messages currently in the mbox file.

        Automatically resets the mailbox unless `reset` is False.
        """
        # We have to use Python 2.4's icky mailbox module until Launchpad
        # upgrades Zope to a Python 2.5 compatible version.
        mbox = mailbox.UnixMailbox(
            open(self._mbox_filename), message_from_file)
        messages = list(mbox)
        if reset:
            self.reset()
        return messages

    def getMailboxSize(self):
        """Return the size in bytes of the mailbox."""
        # Avoid circular imports.
        from lp.services.mailman.testing.helpers import get_size
        # This is never going to be more than an int width so just do the
        # simplest thing to chop off any 'L' that might be there.
        return int(get_size(self._mbox_filename))
