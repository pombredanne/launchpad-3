# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging interfaces."""

__metaclass__ = type
__all__ = [
    'EmptyQueueException',
    'IMessageProducer',
    'IMessageConsumer',
    ]


from zope.interface import Interface


class EmptyQueueException(Exception):
    """Raised if there are no queued messages on a non-blocking read."""


class IMessageConsumer(Interface):

    def receive(blocking=True):
        """Receive data from the queue.

        :raises EmptyQueueException: If non-blocking and the queue is empty.
        """


class IMessageProducer(Interface):

    def send(data):
        """Serialize `data` into JSON and send it to the queue on commit."""

    def send_now(data):
        """Serialize `data` into JSON and send it to the queue immediately."""

    def associateConsumer(consumer):
        """Make the consumer receive messages from this producer.

        :param consumer: An `IMessageConsumer`
        """

    def disassociateConsumer(consumer):
        """Make the consumer stop receiving messages from this producer.

        :param consumer: An `IMessageConsumer`
        """
