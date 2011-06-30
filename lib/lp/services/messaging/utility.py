# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = [
    "LAUNCHPAD_EXCHANGE",
    "messaging",
    ]


from threading import local as thread_local

from amqplib import client_0_8 as amqp
import transaction

from canonical.config import config


LAUNCHPAD_EXCHANGE = "launchpad-exchange"


class MessagingDataManager:
    """A Zope transaction data manager for Launchpad messaging.

    This class implements the necessary code to send messages only when
    the Zope transactions are committed.  It will iterate over the messages
    that are stored in the Message singleton and send them to the message
    broker.
    """
    def __init__(self, messaging_utility):
        self.utility = messaging_utility

    def _cleanup(self):
        """Completely remove the list of stored messages"""
        del self.utility.messages

    def abort(self, txn):
        pass

    def tpc_begin(self, txn):
        pass

    def tpc_vote(self, txn):
        pass

    def tpc_finish(self, txn):
        self._cleanup()

    def tpc_abort(self, txn):
        self._cleanup()

    def sortKey(self):
        """Ensure that rabbit messages are always sent LAST after other parts
        of the transaction are committed."""
        return "zz_messaging_%s" % id(self)

    def commit(self, txn):
        for message in self.utility.locals.messages:
            self.utility._send_now(**message)
        self._cleanup()


class Messaging:
    """Singleton class that provides an API to a message broker."""

    locals = thread_local()

    def initialize(self):
        """Create a connection to the broker."""
        if not hasattr(self.locals, "rabbit"):
            conn = amqp.Connection(
                host=config.rabbitmq.host, userid=config.rabbitmq.userid,
                password=config.rabbitmq.password,
                virtual_host=config.rabbitmq.virtual_host, insist=False)
            self.locals.rabbit = conn
            ch = conn.channel()
            ch.exchange_declare(
                LAUNCHPAD_EXCHANGE, "direct", durable=False,
                auto_delete=False)

    def send(self, routing_key, json_data=None, oncommit=True):
        """Send a message to the broker.

        :param routing_key: This identifies the send point for a message.
            Normally something else would bind a queue name to this routing
            key so that any messages sent to the routing key are multiplexed
            to all the queues.
        :param data: A blob of data to send.  It must be serializable.
        :param oncommit: If True, the data is sent only when the current
            transaction is committed, otherwise it is sent immediately.
        """
        self.initialize()

        if not oncommit:
            self._send_now(routing_key, json_data)
            return

        if not hasattr(self.locals, "messages"):
            self.locals.messages = []
            txn = transaction.get()
            txn.join(MessagingDataManager(self))

        self.locals.messages.append(
            dict(routing_key=routing_key, json_data=json_data))

    def _send_now(self, routing_key, json_data=None):
        """Immediately send a message to the broker."""
        channel = self.locals.rabbit.channel()
        channel.basic_publish(
            exchange=LAUNCHPAD_EXCHANGE,
            routing_key=routing_key,
            msg=amqp.Message(json_data)
            )

    def receive(self, queue_name, blocking=True):
        """Receive a message from the broker.

        :param queue_name: The name of the broker's queue to receive the
            message from.
        :param blocking: If True, wait until a message is received instead of
            returning immediately if there is nothing on the queue.
        """
        channel = self.locals.rabbit.channel()
        result = []

        def callback(msg):
            result.append(msg.body)

        if blocking:
            channel.basic_consume(queue_name, callback=callback, no_ack=True)
            channel.wait()
            return result[0]

        message = channel.basic_get(queue_name)
        return message.body

    def listen(self, queue_name, routing_key):
        """Create a new transient queue and bind it to `routing_key`.

        If the queue already exists this just binds `routing_key` in addition
        to previous binds.
        """
        self.initialize()
        channel = self.locals.rabbit.channel()
        channel.queue_declare(queue_name, auto_delete=True)
        channel.queue_bind(
            queue=queue_name, exchange=LAUNCHPAD_EXCHANGE,
            routing_key=routing_key)


# Messaging() is a singleton.
messaging = Messaging()
