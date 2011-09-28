# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = [
    "session",
    "unreliable_session",
    ]

from collections import deque
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
    EmptyQueue,
    IMessageConsumer,
    IMessageProducer,
    IMessageSession,
    MessagingException,
    MessagingUnavailable,
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

    exchange = LAUNCHPAD_EXCHANGE

    def __init__(self):
        super(RabbitSession, self).__init__()
        self._connection = None
        self._deferred = deque()
        # Maintain sessions according to transaction boundaries. Keep a strong
        # reference to the sync because the transaction manager does not. We
        # need one per thread (definining it here is enough to ensure that).
        self._sync = RabbitSessionTransactionSync(self)
        transaction.manager.registerSynch(self._sync)

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
            if (config.rabbitmq.host is None or
                config.rabbitmq.userid is None or
                config.rabbitmq.password is None or
                config.rabbitmq.virtual_host is None):
                raise MessagingUnavailable("Incomplete configuration")
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

    def flush(self):
        """See `IMessageSession`."""
        tasks = self._deferred
        while len(tasks) != 0:
            tasks.popleft()()

    def finish(self):
        """See `IMessageSession`."""
        try:
            self.flush()
        finally:
            self.reset()

    def reset(self):
        """See `IMessageSession`."""
        self._deferred.clear()
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


class RabbitUnreliableSession(RabbitSession):
    """An "unreliable" `RabbitSession`.

    Unreliable in this case means that certain errors in deferred tasks are
    silently suppressed, `AMQPException` in particular. This means that
    services can continue to function even in the absence of a running and
    fully functional message queue.
    """

    ignored_errors = (
        IOError,
        MessagingException,
        amqp.AMQPException,
        )

    def finish(self):
        """See `IMessageSession`.

        Suppresses errors listed in `ignored_errors`.
        """
        try:
            super(RabbitUnreliableSession, self).finish()
        except self.ignored_errors:
            pass


# Per-thread "unreliable" sessions.
unreliable_session = RabbitUnreliableSession()


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
            self._channel.exchange_declare(
                self.session.exchange, "direct", durable=False,
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
            queue=consumer.name, exchange=self.session.exchange,
            routing_key=self.key, nowait=False)

    def send(self, data):
        """See `IMessageProducer`."""
        self.session.defer(self.sendNow, data)

    def sendNow(self, data):
        """Immediately send a message to the broker."""
        json_data = json.dumps(data)
        msg = amqp.Message(json_data)
        self.channel.basic_publish(
            exchange=self.session.exchange,
            routing_key=self.key, msg=msg)


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
        :raises EmptyQueue: if the timeout passes.
        """
        starttime = time.time()
        while True:
            message = self.channel.basic_get(self.name)
            if message is None:
                if time.time() > (starttime + timeout):
                    raise EmptyQueue()
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
