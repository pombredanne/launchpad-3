# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging interfaces."""

__metaclass__ = type
__all__ = [
    'EmptyQueueException',
    'IMessageQueue',
    ]


from zope.interface import Interface


class EmptyQueueException(Exception):
    """Raised if there are no queued messages on a non-blocking read."""
    pass


class IMessageQueue(Interface):
    def send(key, data):
        """Serialize `data` into JSON and send it to the queue on commit."""

    def send_now(key, data):
        """Serialize `data` into JSON and send it to the queue immediately."""

    def receive(blocking=True):
        """Receive data from the queue.

        :raises EmptyQueueException: If non-blocking and the queue is empty.
        """
