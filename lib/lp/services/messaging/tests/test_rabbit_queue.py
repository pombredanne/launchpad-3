# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging utility tests."""

__metaclass__ = type

from itertools import count

import transaction
from transaction._transaction import Status as TransactionStatus

from canonical.testing.layers import RabbitMQLayer
from lp.services.messaging.interfaces import (
    EmptyQueueException,
    IMessageConsumer,
    IMessageProducer,
    IMessageSession,
    )
from lp.services.messaging.queue import (
    RabbitMessageBase,
    RabbitQueue,
    RabbitRoutingKey,
    RabbitSession,
    RabbitSessionTransactionSync,
    )
from lp.testing import TestCase
from lp.testing.faketransaction import FakeTransaction
from lp.testing.matchers import Provides

# RabbitMQ is not (yet) torn down or reset between tests, so here are sources
# of distinct names.
queue_names = ("queue.%d" % num for num in count(1))
key_names = ("key.%d" % num for num in count(1))


class FakeRabbitSession:

    def __init__(self):
        self.log = []

    def finish(self):
        self.log.append("finish")

    def reset(self):
        self.log.append("reset")


class TestRabbitSessionTransactionSync(TestCase):

    def test_interface(self):
        self.assertThat(
            RabbitSessionTransactionSync(None),
            Provides(transaction.interfaces.ISynchronizer))

    def test_afterCompletion_COMMITTED(self):
        txn = FakeTransaction()
        txn.status = TransactionStatus.COMMITTED
        session = FakeRabbitSession()
        sync = RabbitSessionTransactionSync(session)
        sync.afterCompletion(txn)
        self.assertEqual(["finish"], session.log)

    def test_afterCompletion_ACTIVE(self):
        txn = FakeTransaction()
        txn.status = TransactionStatus.ACTIVE
        session = FakeRabbitSession()
        sync = RabbitSessionTransactionSync(session)
        sync.afterCompletion(txn)
        self.assertEqual(["reset"], session.log)


class RabbitTestCase(TestCase):

    layer = RabbitMQLayer

    def tearDown(self):
        super(RabbitTestCase, self).tearDown()
        RabbitMessageBase.session.disconnect()


class TestRabbitSession(RabbitTestCase):

    def test_interface(self):
        session = RabbitSession()
        self.assertThat(session, Provides(IMessageSession))

    def test_connect(self):
        session = RabbitSession()
        self.assertIs(None, session.connection)
        connection = session.connect()
        self.assertIsNot(None, session.connection)
        self.assertIs(connection, session.connection)

    def test_disconnect(self):
        session = RabbitSession()
        session.connect()
        session.disconnect()
        self.assertIs(None, session.connection)

    def test_connection(self):
        # The connection property is None once a connection has been closed.
        session = RabbitSession()
        session.connect()
        # Close the connection without using disconnect().
        session.connection.close()
        self.assertIs(None, session.connection)


class TestRabbitMessageBase(RabbitTestCase):

    def test_session(self):
        base = RabbitMessageBase()
        self.assertIsInstance(base.session, RabbitSession)

    def test_channel(self):
        # Referencing the channel property causes the session to connect.
        base = RabbitMessageBase()
        self.assertIs(None, base.session.connection)
        channel = base.channel
        self.assertIsNot(None, base.session.connection)
        self.assertIsNot(None, channel)
        # The same channel is returned every time.
        self.assertIs(channel, base.channel)

    def test_channel_session_closed(self):
        # When the session is disconnected the channel is thrown away too.
        base = RabbitMessageBase()
        channel1 = base.channel
        base.session.disconnect()
        channel2 = base.channel
        self.assertNotEqual(channel1, channel2)


class TestRabbitRoutingKey(RabbitTestCase):

    def test_interface(self):
        routing_key = RabbitRoutingKey(next(key_names))
        self.assertThat(routing_key, Provides(IMessageProducer))

    def test_associateConsumer(self):
        # associateConsumer() only associates the consumer at transaction
        # commit time. However, order is preserved.
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumer(consumer)
        routing_key.sendNow('now')
        routing_key.send('later')
        # There is nothing in the queue because the consumer has not yet been
        # associated with the routing key.
        self.assertRaises(EmptyQueueException, consumer.receive, timeout=2)
        transaction.commit()
        # Now that the transaction has been committed, the consumer is
        # associated, and receives the deferred message.
        self.assertEqual('later', consumer.receive(timeout=2))

    def test_associateConsumerNow(self):
        # associateConsumerNow() associates the consumer right away.
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)
        routing_key.sendNow('now')
        routing_key.send('later')
        # There is already something in the queue.
        self.assertEqual('now', consumer.receive(timeout=2))
        transaction.commit()
        # Now that the transaction has been committed there is another item in
        # the queue.
        self.assertEqual('later', consumer.receive(timeout=2))

    def test_send(self):
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)

        for data in range(90, 100):
            routing_key.send(data)

        routing_key.sendNow('sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual('sync', consumer.receive(timeout=2))

        # Messages get sent on commit
        transaction.commit()
        for data in range(90, 100):
            self.assertEqual(data, consumer.receive())

        # There are no more messages. They have all been consumed.
        routing_key.sendNow('sync')
        self.assertEqual('sync', consumer.receive(timeout=2))

    def test_sendNow(self):
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)

        for data in range(50, 60):
            routing_key.sendNow(data)
            received_data = consumer.receive(timeout=2)
            self.assertEqual(data, received_data)


class TestRabbitQueue(RabbitTestCase):

    def test_interface(self):
        consumer = RabbitQueue(next(queue_names))
        self.assertThat(consumer, Provides(IMessageConsumer))

    def test_receive(self):
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)

        for data in range(55, 65):
            routing_key.sendNow(data)
            self.assertEqual(data, consumer.receive(timeout=2))

        # All the messages received were consumed.
        self.assertRaises(
            EmptyQueueException,
            consumer.receive, timeout=2)

        # New connections to the queue see an empty queue too.
        consumer.session.disconnect()
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)
        self.assertRaises(
            EmptyQueueException,
            consumer.receive, timeout=2)


class TestRabbit(RabbitTestCase):
    """Integration-like tests for the RabbitMQ messaging abstractions."""

    def test_abort(self):
        consumer = RabbitQueue(next(queue_names))
        routing_key = RabbitRoutingKey(next(key_names))
        routing_key.associateConsumerNow(consumer)

        for data in range(90, 100):
            routing_key.send(data)

        # Messages sent using send() are forgotten on abort.
        transaction.abort()
        self.assertRaises(
            EmptyQueueException,
            consumer.receive, timeout=2)
