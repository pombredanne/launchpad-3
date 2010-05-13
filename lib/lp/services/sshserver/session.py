# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Patched SSH session for the Launchpad server."""

__metaclass__ = type
__all__ = [
    'PatchedSSHSession',
    ]

from twisted.conch.ssh import channel, session


class PatchedSSHSession(session.SSHSession, object):
    """Session adapter that corrects bugs in Conch.

    This object provides no custom logic for Launchpad, it just addresses some
    simple bugs in the base `session.SSHSession` class that are not yet fixed
    upstream.
    """

    def closeReceived(self):
        # Without this, the client hangs when it's finished transferring.
        # XXX: JonathanLange 2009-01-05: This does not appear to have a
        # corresponding bug in Twisted. We should test that the above comment
        # is indeed correct and then file a bug upstream.
        self.loseConnection()

    def loseConnection(self):
        # XXX: JonathanLange 2008-03-31: This deliberately replaces the
        # implementation of session.SSHSession.loseConnection. The default
        # implementation will try to call loseConnection on the client
        # transport even if it's None. I don't know *why* it is None, so this
        # doesn't necessarily address the root cause.
        # See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            transport.loseConnection()
        # This is called by session.SSHSession.loseConnection. SSHChannel is
        # the base class of SSHSession.
        channel.SSHChannel.loseConnection(self)

    def stopWriting(self):
        """See `session.SSHSession.stopWriting`.

        When the client can't keep up with us, we ask the child process to
        stop giving us data.
        """
        # XXX: MichaelHudson 2008-06-27: Being cagey about whether
        # self.client.transport is entirely paranoia inspired by the comment
        # in `loseConnection` above. It would be good to know if and why it is
        # necessary. See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            # For SFTP connections, 'transport' is actually a _DummyTransport
            # instance. Neither _DummyTransport nor the protocol it wraps
            # (filetransfer.FileTransferServer) support pausing.
            pauseProducing = getattr(transport, 'pauseProducing', None)
            if pauseProducing is not None:
                pauseProducing()

    def startWriting(self):
        """See `session.SSHSession.startWriting`.

        The client is ready for data again, so ask the child to start
        producing data again.
        """
        # XXX: MichaelHudson 2008-06-27: Being cagey about whether
        # self.client.transport is entirely paranoia inspired by the comment
        # in `loseConnection` above. It would be good to know if and why it is
        # necessary. See http://twistedmatrix.com/trac/ticket/2754.
        transport = getattr(self.client, 'transport', None)
        if transport is not None:
            # For SFTP connections, 'transport' is actually a _DummyTransport
            # instance. Neither _DummyTransport nor the protocol it wraps
            # (filetransfer.FileTransferServer) support pausing.
            resumeProducing = getattr(transport, 'resumeProducing', None)
            if resumeProducing is not None:
                resumeProducing()
