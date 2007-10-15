# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad-Mailman integration test #5

Only Launchpad members are allowed to post.
"""

import os
import sys
import errno
import socket
import mailbox
import tempfile
import itest_helper

from email import message_from_file
from Mailman.mm_cfg import LOG_DIR

from canonical.config import config


def mboxiter(mbox_filename):
    """Helper for iterating over the messages in a mailbox."""
    mbox = mailbox.UnixMailbox(open(mbox_filename), message_from_file)
    for message in mbox:
        yield message


def get_temp_filename():
    """Return just the file name for a temporary file."""
    descriptor, filename = tempfile.mkstemp()
    os.close(descriptor)
    return filename


def size(filename):
    """Return the size of the named file, or -1 if it doesn't exist."""
    try:
        return os.stat(filename).st_size
    except OSError, error:
        if error.errno == errno.ENOENT:
            # Return -1 when the file does not exist, so it always compares
            # less than an existing but empty file.
            return -1
        # Some other error occurred.
        raise


def file_has_grown(filename, last_size):
    """Poll function for file growth."""
    def poll_function():
        return size(filename) > last_size
    return poll_function


def smtpd_is_listening():
    """Poll function to make sure our smtpd has started."""
    s = socket.socket()
    try:
        s.connect(config.mailman.smtp)
        s.setblocking(0)
        s.send('QUIT\r\n')
        s.close()
        return True
    except socket.error:
        return False


def exit_smtpd():
    """Poll function to make sure our smtpd has exited."""
    s = socket.socket()
    try:
        s.connect(config.mailman.smtp)
        s.setblocking(0)
        s.send('EXIT\r\n')
        return True
    except socket.error:
        return False


def parent(mbox_filename):
    """The parent process; i.e. the main tests."""
    # Get the size of a Mailman log file before it can grow due to the
    # following test.
    mailman_log_file = os.path.join(LOG_DIR, 'vette')
    current_size = size(mailman_log_file)
    # Inject a message from a non-member into the Mailman incoming queue.
    # This should get discarded by the handler that assures the poster is a
    # Launchpad member.  We can tell this by the fact that the mbox file will
    # stay empty.
    message_filename = get_temp_filename()
    message_file = open(message_filename, 'w')
    try:
        print >> message_file, """\
From: zperson@example.net
To: team-one@lists.launchpad.net
Subject: A non-member post

Hi, I am not a member of Launchpad (yet).
"""
        message_file.close()
        itest_helper.run_mailman(
            './inject', '-l', 'team-one', message_filename)
    finally:
        os.remove(message_filename)
    # Poll until the log file has grown.  When it has, we know that Mailman
    # has processed the injected message.
    itest_helper.poll(file_has_grown(mailman_log_file, current_size))
    if os.path.getsize(mbox_filename) > 0:
        raise itest_helper.IntegrationTestFailure(
            'Unexpected mbox file contents')
    # Now send a message from a Launchpad member.  This one gets delivered.
    current_size = size(mbox_filename)
    message_file = open(message_filename, 'w')
    try:
        print >> message_file, """\
From: aperson@example.org
To: team-one@lists.launchpad.net
Subject: A member post

Hi, I am a member of Launchpad.
"""
        message_file.close()
        itest_helper.run_mailman(
            './inject', '-l', 'team-one', message_filename)
    finally:
        os.remove(message_filename)
    # This time, wait for the mbox file to grow, since it will contain the
    # posted messages.
    itest_helper.poll(file_has_grown(mbox_filename, current_size))
    # Read the messages from the mbox file.  Because we are not personalizing
    # delivery and because we have two .com recipients and one .org recipient,
    # we should have exactly two copies of the message in the mbox file.  This
    # is because of Mailman's per-TLD chunking algorithm.
    messages = list(mboxiter(mbox_filename))
    if len(messages) != 2:
        raise itest_helper.IntegrationTestFailure(
            'Expected 2 messages in the mbox, got: %s' % len(messages))
    if str(messages[0]) != str(messages[1]):
        raise itest_helper.IntegrationTestFailure('Copies are different')
    message = messages[0]
    if (message['subject'] != '[Team-one] A member post' or
        message['from'] != 'aperson@example.org' or
        message['to'] != 'team-one@lists.launchpad.net'):
        # This is not the message we are looking for.
        raise itest_helper.IntegrationTestFailure(
            'Did not get the message we expected')


def main():
    """End-to-end testing for posting privileges."""
    # First, start our mboxing test SMTP server.
    mbox_filename = get_temp_filename()
    pid = os.fork()
    if pid == 0:
        # Child
        server_path = os.path.join(itest_helper.HERE, 'smtp2mbox')
        os.execl(sys.executable, sys.executable, server_path, mbox_filename)
        # We should never get here!
        os._exit(-1)
    try:
        # Parent
        itest_helper.poll(smtpd_is_listening)
        parent(mbox_filename)
    finally:
        itest_helper.poll(exit_smtpd)
        os.waitpid(pid, 0)
        try:
            os.remove(mbox_filename)
        except OSError:
            pass
