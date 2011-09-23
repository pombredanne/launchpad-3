# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = [
    "session",
    ]

from functools import partial
import json
import threading
import time

from amqplib import client_0_8 as amqp
import transaction
from transaction._transaction import Status as TransactionStatus
from zope.interface import implements

from canonical.config import config
from lp.services.messaging.interfaces import (
    EmptyQueueException,
    IMessageConsumer,
    IMessageProducer,
    IMessageSession,
    )


LAUNCHPAD_EXCHANGE = "launchpad-exchange"


class RabbitSessionTransactionSync:

    implements(transaction.interfaces.ISynchronizer)

    def __init__(self, session):
        self.session = session

    def newTransaction(self, txn):
        pass

    def beforeCompletion(self, txn):
        pass

    def afterCompletion(self, txn):
        if txn.status == TransactionStatus.COMMITTED:
            self.session.finish()
        else:
            self.session.reset()


class RabbitSession(threading.local):

    implements(IMessageSession)

    def __init__(self):
        self._connection = None
        self._deferred = []

    @property
    def connection(self):
        """See `IMessageSession`.

        Don't return closed connection.
        """
        if self._connection is None:
            return None
        elif self._connection.transport is None:
            return None
        else:
            return self._connection

    def connect(self):
        """See `IMessageSession`.

        Open a connection for this thread if necessary. Connections cannot be
        shared between threads.
        """
        if self._connection is None or self._connection.transport is None:
            self._connection = amqp.Connection(
                host=config.rabbitmq.host, userid=config.rabbitmq.userid,
                password=config.rabbitmq.password,
                virtual_host=config.rabbitmq.virtual_host, insist=False)
        return self._connection

    def disconnect(self):
        """See `IMessageSession`."""
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    def finish(self):
        """See `IMessageSession`."""
        try:
            for action in self._deferred:
                action()
        finally:
            self.reset()

    def reset(self):
        """See `IMessageSession`."""
        del self._deferred[:]
        self.disconnect()

    def defer(self, func, *args, **kwargs):
        """See `IMessageSession`."""
        self._deferred.append(partial(func, *args, **kwargs))

    def getProducer(self, name):
        """See `IMessageSession`."""
        return RabbitRoutingKey(self, name)

    def getConsumer(self, name):
        """See `IMessageSession`."""
        return RabbitQueue(self, name)


# Per-thread sessions.
session = RabbitSession()

# Maintain the per-thread sessions according to transaction boundaries. Keep a
# strong reference to the sync because the transaction manager does not.
session_sync = RabbitSessionTransactionSync(session)
transaction.manager.registerSynch(session_sync)


class RabbitMessageBase:
    """Base class for all RabbitMQ messaging."""

    def __init__(self, session):
        self.session = IMessageSession(session)
        self._channel = None

    @property
    def channel(self):
        if self._channel is None or not self._channel.is_open:
            connection = self.session.connect()
            self._channel = connection.channel()
            #self._channel.access_request(
            #    '/data', active=True, write=True, read=True)
            self._channel.exchange_declare(
                LAUNCHPAD_EXCHANGE, "direct", durable=False,
                auto_delete=False, nowait=False)
        return self._channel


class RabbitRoutingKey(RabbitMessageBase):
    """A RabbitMQ data origination point."""

    implements(IMessageProducer)

    def __init__(self, session, routing_key):
        super(RabbitRoutingKey, self).__init__(session)
        self.key = routing_key

    def associateConsumer(self, consumer):
        """Only receive messages for requested routing key."""
        self.session.defer(self.associateConsumerNow, consumer)

    def associateConsumerNow(self, consumer):
        """Only receive messages for requested routing key."""
        self.channel.queue_bind(
            queue=consumer.name, exchange=LAUNCHPAD_EXCHANGE,
            routing_key=self.key, nowait=False)

    def send(self, data):
        """See `IMessageProducer`."""
        self.session.defer(self.sendNow, data)

    def sendNow(self, data):
        """Immediately send a message to the broker."""
        json_data = json.dumps(data)
        msg = amqp.Message(json_data)
        self.channel.basic_publish(
            exchange=LAUNCHPAD_EXCHANGE, routing_key=self.key, msg=msg)


class RabbitQueue(RabbitMessageBase):
    """A RabbitMQ Queue."""

    implements(IMessageConsumer)

    def __init__(self, session, name):
        super(RabbitQueue, self).__init__(session)
        self.name = name
        self.channel.queue_declare(self.name, nowait=False)

    def receive(self, timeout=0.0):
        """Pull a message from the queue.

        :param timeout: Wait a maximum of `timeout` seconds before giving up,
            trying at least once.
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
