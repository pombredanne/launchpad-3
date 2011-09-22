# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = [
    "RabbitRoutingKey",
    "RabbitQueue",
    ]

from functools import partial
import json
from threading import local as thread_local
import time

from amqplib import client_0_8 as amqp
import transaction
from zope.interface import implements

from canonical.config import config
from lp.services.messaging.interfaces import (
    EmptyQueueException,
    IMessageConsumer,
    IMessageProducer,
    )


LAUNCHPAD_EXCHANGE = "launchpad-exchange"


class MessagingDataManager:
    """A Zope transaction data manager for Launchpad messaging.

    This class implements the necessary code to interact with RabbitMQ only
    when the Zope transactions are committed.
    """

    implements(transaction.interfaces.IDataManager)

    def __init__(self, actions):
        self.transaction_manager = transaction.manager
        self.actions = actions

    def _cleanup(self):
        """Completely remove the list of actions."""
        del self.actions[:]

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
        """Execute actions after PostgresSQL connections are committed."""
        return "zz_messaging_%s" % id(self)

    def commit(self, txn):
        try:
            for action in self.actions:
                action()
        finally:
            self._cleanup()


class RabbitMessageBase:
    """Base class for all RabbitMQ messaging."""

    class_locals = thread_local()

    channel = None

    def _initialize(self):
        # Open a connection and channel for this thread if necessary.
        # Connections cannot be shared between threads.
        if not hasattr(self.class_locals, "rabbit_connection"):
            conn = amqp.Connection(
                host=config.rabbitmq.host, userid=config.rabbitmq.userid,
                password=config.rabbitmq.password,
                virtual_host=config.rabbitmq.virtual_host, insist=False)
            self.class_locals.rabbit_connection = conn

            # Initialize storage for oncommit messages.
            self.class_locals.deferred_actions = []

        conn = self.class_locals.rabbit_connection
        self.channel = conn.channel()
        #self.channel.access_request(
        #    '/data', active=True, write=True, read=True)
        self.channel.exchange_declare(
            LAUNCHPAD_EXCHANGE, "direct", durable=False,
            auto_delete=False, nowait=False)

    def close(self):
        # Note the connection is not closed - it is shared with other
        # queues. Just close our channel.
        if self.channel:
            self.channel.close()

    def _disconnect(self):
        """Disconnect from rabbit. The connection is shared, so this will
        break other RabbitQueue instances."""
        self.close()
        if hasattr(self.class_locals, 'rabbit_connection'):
            self.class_locals.rabbit_connection.close()
            del self.class_locals.rabbit_connection


class RabbitRoutingKey(RabbitMessageBase):
    """A RabbitMQ data origination point."""

    implements(IMessageProducer)

    def __init__(self, routing_key):
        self.key = routing_key

    def associateConsumer(self, consumer):
        """Only receive messages for requested routing key."""
        self._initialize()
        self.channel.queue_bind(
            queue=consumer.name, exchange=LAUNCHPAD_EXCHANGE,
            routing_key=self.key, nowait=False)

    def disassociateConsumer(self, consumer):
        """Stop receiving messages for the requested routing key."""
        self._initialize()
        self.channel.queue_unbind(
            queue=consumer.name, exchange=LAUNCHPAD_EXCHANGE,
            routing_key=self.key, nowait=False)

    def send(self, data):
        """See `IMessageProducer`."""
        self._initialize()
        actions = self.class_locals.deferred_actions
        # XXX: The data manager should close channels and flush too
        if len(actions) == 0:
            transaction.get().join(MessagingDataManager(actions))
        actions.append(partial(self.send_now, data))

    def send_now(self, data):
        """Immediately send a message to the broker."""
        self._initialize()
        json_data = json.dumps(data)
        msg = amqp.Message(json_data)
        self.channel.basic_publish(
            exchange=LAUNCHPAD_EXCHANGE, routing_key=self.key, msg=msg)


class RabbitQueue(RabbitMessageBase):
    """A RabbitMQ Queue."""

    implements(IMessageConsumer)

    def __init__(self, name):
        self.name = name
        self._initialize()
        self.channel.queue_declare(self.name, nowait=False)

    def receive(self, timeout=0.0):
        """Pull a message from the queue.

        :param timeout: Wait a maximum of `timeout` seconds before giving up,
            trying at least once.  If timeout is None, block forever.
        :raises: EmptyQueueException if the timeout passes.
        """
        starttime = time.time()
        while True:
            message = self.channel.basic_get(self.name)
            if message is None:
                if time.time() > (starttime + timeout):
                    raise EmptyQueueException
                time.sleep(0.1)
            else:
                data = json.loads(message.body)
                self.channel.basic_ack(message.delivery_tag)
                return data

        # XXX The code below will be useful when we can implement this
        # properly.
        result = []

        def callback(msg):
            result.append(json.loads(msg.body))

        self.channel.basic_consume(self.name, callback=callback)
        self.channel.wait()
        return result[0]
