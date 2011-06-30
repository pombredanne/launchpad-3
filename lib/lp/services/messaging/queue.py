# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = [
    "messaging"
    ]

from amqplib import client_0_8 as amqp
import json
from threading import local as thread_local
import transaction
from zope.interface import implements

from canonical.config import config
from lp.services.messaging.interfaces import (
    IMessageQueue,
    EmptyQueueException,
    )

LAUNCHPAD_EXCHANGE = "launchpad-exchange"


class MessagingDataManager:
    """A Zope transaction data manager for Launchpad messaging.

    This class implements the necessary code to send messages only when
    the Zope transactions are committed.  It will iterate over the messages
    and send them using queue.send(oncommit=False).
    """
    def __init__(self, messages):
        self.messages = messages

    def _cleanup(self):
        """Completely remove the list of stored messages"""
        del self.messages[:]

    def abort(self, txn):
        self._cleanup()

    def tpc_begin(self, txn):
        pass

    def tpc_vote(self, txn):
        pass

    def tpc_finish(self, txn):
        self._cleanup()

    def tpc_abort(self, txn):
        self._cleanup()

    def sortKey(self):
        """Ensure that messages are sent after PostgresSQL connections
        are committed."""
        return "zz_messaging_%s" % id(self)

    def commit(self, txn):
        for queue, key, data in self.messages:
            queue.send(key, data, oncommit=False)
        self._cleanup()


class RabbitQueue:
    """A RabbitMQ Queue."""

    implements(IMessageQueue)

    class_locals = thread_local()

    def __init__(self, name):
        self.name = name

    def _initialize(self):
        # Open a connection and channel for this thread if necessary.
        # Connections cannot be shared between threads.
        if not hasattr(self.class_locals, "rabbit_connection"):
            conn = amqp.Connection(
                host=config.rabbitmq.host, userid=config.rabbitmq.userid,
                password=config.rabbitmq.password,
                virtual_host=config.rabbitmq.virtual_host, insist=False)
            self.class_locals.rabbit_connection = conn
            self.channel = conn.channel()
            self.channel.exchange_declare(
                LAUNCHPAD_EXCHANGE, "direct", durable=False,
                auto_delete=False)

            # Initialize storage for oncommit messages.
            self.class_locals.messages = []
        else:
            self.channel = self.class_locals.rabbit_connection.channel()

        self.channel.queue_declare(self.name)

    def subscribe(self, key):
        """Only receive messages for requested routing keys."""
        self._initialize()
        self.channel.queue_bind(
            queue=self.name, exchange=LAUNCHPAD_EXCHANGE,
            routing_key=key)

    def send(self, key, data):
        """See `IMessageQueue`."""
        self._initialize()
        messages = self.class_locals.messages
        if not messages:
            transaction.get().join(MessagingDataManager(messages))
        messages.append((self.send_now, key, data))

    def send_now(self, key, data):
        """Immediately send a message to the broker."""
        self._initialize()
        json_data = json.dumps(data)
        msg = amqp.Message(json_data)
        self.channel.basic_publish(
            exchange=LAUNCHPAD_EXCHANGE, routing_key=key, msg=msg)

    def receive(self, blocking=True):
        """Pull a message from the queue.

        :param blocking: If True, wait until a message is received instead of
            returning immediately if there is nothing on the queue.
        """
        self._initialize()

        if not blocking:
            message = self.channel.basic_get(self.name)
            if message is None:
                # We need to raise an exception, as None is a legitimate
                # return value.
                raise EmptyQueueException()
            else:
                return json.loads(message.body)

        # Hacked blocking get
        import time
        while True:
            message = self.channel.basic_get(self.name)
            if message is None:
                time.sleep(0.1)
            else:
                return json.loads(message.body)


        result = []
        def callback(msg):
            result.append(json.loads(msg.body))

        self.channel.basic_consume(
            self.name, callback=callback, no_ack=True)
        self.channel.wait()
        return result[0]
