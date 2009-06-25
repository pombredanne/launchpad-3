#! /usr/bin/env python2.4
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Throw email messages into an mbox file.

This starts an SMTP server listening on a port that the Mailman integration
tests will send their messages to.  It is started in tests that need to check
end-to-end message delivery, using fork/exec.

Because we must use Python 2.4, we can't use the wizzy new mailbox module, so
just write messages to the file.
"""

import os
import sys
import smtpd
import signal
import socket
import asyncore

from email import message_from_string
from optparse import OptionParser

import logging
log = logging.getLogger('smtpd')

FMT     = '%(asctime)s (%(process)d) %(message)s'
DATEFMT = '%b %d %H:%M:%S %Y'


class ResettingChannel(smtpd.SMTPChannel):
    """A channel that can reset the temporary file."""

    def __init__(self, server, conn, addr):
        smtpd.SMTPChannel.__init__(self, server, conn, addr)
        # Stash this here since the subclass uses private attributes. :(
        self._server = server

    def smtp_RSET(self, arg):
        """Reset the mbox file on the server instance."""
        self._server.resetMailboxFile()
        smtpd.SMTPChannel.smtp_RSET(self, arg)

    def send(self, data):
        """Silence the bloody asynchat/asyncore broken pipe errors!"""
        try:
            return smtpd.SMTPChannel.send(self, data)
        except socket.error:
            # Nothing here can affect the outcome, and these messages are just
            # plain annoying!  So ignore them.
            pass


class Server(smtpd.SMTPServer):
    """An SMTP server subclass that stores to an mbox file."""
    def __init__(self, parser):
        addr = (parser.options.host, parser.options.port)
        smtpd.SMTPServer.__init__(self, addr , None)
        self._mbox_file = parser.options.mbox
        self.resetMailboxFile()
        sys.path.insert(0, parser.options.path)

    def handle_accept(self):
        """Open a resetting channel."""
        conn, addr = self.accept()
        log.debug('accept: %s', addr)
        channel = ResettingChannel(self, conn, addr)
        # Do not dispatch to the base class, since that would create a second
        # channel that we don't want, and wouldn't support the extended RSET
        # command anyway.

    def resetMailboxFile(self):
        """Re-open the mailbox file."""
        self._mbox = open(self._mbox_file, 'w')
        log.debug('Resetting mbox file: %s', self._mbox_file)

    def process_message(self, peer, mailfrom, rcpttos, data):
        """Deliver a message.

        The message is either delivered to the mbox file specified on the
        command line, the local host's real SMTPd, or it is dropped into
        Mailman's incoming queue.
        """
        message = message_from_string(data)
        message['Received'] = 'by smtp2mbox'
        # Get the localpart of the recipient.  If this localpart corresponds
        # to an existing mailing list, drop the message into Mailman's
        # incoming queue.
        log.debug('msgid: %s, to: %s, beenthere: %s rcpt: %s',
                  message['message-id'], message['to'],
                  message['x-beenthere'], rcpttos)
        try:
            local, hostname = message['to'].split('@', 1)
        except ValueError:
            # There was no '@' sign in the email message, so let the upstream
            # SMTPd handle the message.
            log.debug('Bad TO header: %s', message.get('to', 'n/a'))
            return
        # If the message came from Mailman, drop it in the mbox (this must be
        # tested first).  If the local part indicates that the message is
        # destined for a Mailman mailing list, deliver it to Mailman's
        # incoming queue.  Otherwise, deliver it to the upstream SMTPd.
        # pylint: disable-msg=F0401
        from Mailman.Utils import list_names
        if 'x-beenthere' in message:
            # It came from Mailman and goes to the mbox.
            self._deliver_to_mbox(message)
        elif local in list_names():
            # It's destined for a mailing list.
            self._deliver_to_mailman(local, message)
        # Otherwise, it's destined for a 'normal' user.  Store this in the
        # mbox so the doctests can check it.
        else:
            self._deliver_to_mbox(message)

    def _deliver_to_mailman(self, listname, message):
        """Deliver the message to Mailman's incoming queue."""
        # pylint: disable-msg=F0401
        from Mailman.Post import inject
        inject(listname, message)
        log.debug(
            'delivered to mailman: %s', message.get('message-id', 'n/a'))

    def _deliver_to_mbox(self, message):
        """Store the message in the mbox."""
        print >> self._mbox, message
        print >> self._mbox
        self._mbox.flush()
        os.fsync(self._mbox.fileno())
        log.debug('delivered to mbox: %s', message.get('message-id', 'n/a'))

    def close(self):
        """Close the mbox file."""
        self._mbox.close()


def handle_signal(*ignore):
    """Handle signal sent by parent to kill the process."""
    # Why is killing an asyncore loop so painful?  There appears to be no way
    # to do this cleanly without either reimplementing asyncore.loop() as Zope
    # does, or getting an "uncaptured python exception" deep inside asyncore.
    # For simplicity's sake I can live with that annoying non-fatal error.
    asyncore.socket_map.clear()


def parse_arguments():
    parser = OptionParser()
    parser.add_option('--host', default='localhost', action='store')
    parser.add_option('--port', default=25, type='int')
    parser.add_option('--mbox', action='store')
    parser.add_option('--path', action='store')
    parser.add_option('--logfile', action='store', default='smtpd.log')
    options, arguments = parser.parse_args()
    parser.options = options
    parser.arguments = arguments
    return parser


if __name__ == '__main__':
    # Catch the parent's exit signal, and also C-c.
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    parser = parse_arguments()

    # Set up logging.
    logging.basicConfig(format=FMT, datefmt=DATEFMT, level=logging.INFO)
    filelog = logging.FileHandler(parser.options.logfile)
    formatter = logging.Formatter(fmt=FMT, datefmt=DATEFMT)
    filelog.setFormatter(formatter)
    log.addHandler(filelog)
    log.setLevel(logging.DEBUG)
    log.propagate = False

    # Run the main loop.
    server = Server(parser)
    log.debug('SMTP listener started on: %s:%s',
              parser.options.host, parser.options.port)
    asyncore.loop()
    asyncore.close_all()
    server.close()
