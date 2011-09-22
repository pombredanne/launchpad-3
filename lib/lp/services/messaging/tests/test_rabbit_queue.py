# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging utility tests."""

__metaclass__ = type

import transaction

from canonical.testing.layers import RabbitMQLayer
from lp.services.messaging.interfaces import (
    EmptyQueueException,
    IMessageConsumer,
    IMessageProducer,
    )
from lp.services.messaging.queue import (
    MessagingDataManager,
    RabbitQueue,
    RabbitRoutingKey,
    )
from lp.testing import TestCase
from lp.testing.matchers import Provides


class TestRabbitQueue(TestCase):

    layer = RabbitMQLayer

    def setUp(self):
        super(TestCase, self).setUp()
        self.queue_name = 'whatever'
        self.queue = RabbitQueue(self.queue_name)
        self.key_name = "arbitrary.routing.key"
        self.key = RabbitRoutingKey(self.key_name)
        self.key.associateConsumer(self.queue)

    def tearDown(self):
        self.queue.session.connection.close()
        super(TestCase, self).tearDown()

    def test_interfaces(self):
        self.assertThat(self.queue, Provides(IMessageConsumer))
        self.assertThat(self.key, Provides(IMessageProducer))
        self.assertThat(
            MessagingDataManager(),
            Provides(transaction.interfaces.IDataManager))

    def test_send_now(self):
        for data in range(50, 60):
            self.key.send_now(data)
            received_data = self.queue.receive(timeout=5)
            self.assertEqual(received_data, data)

    def test_receive_consumes(self):
        for data in range(55, 65):
            self.key.send_now(data)
            self.assertEqual(self.queue.receive(timeout=5), data)

        # None of the messages we received were put back. They were all
        # consumed.
        self.assertRaises(
            EmptyQueueException,
            self.queue.receive, timeout=5)

        # New connections to the queue see an empty queue too.
        self.queue.session.connection.close()
        key = RabbitRoutingKey(self.key_name)
        queue = RabbitQueue(self.queue_name)
        key.associateConsumer(queue)
        key.send_now('new conn sync')
        self.assertEqual(queue.receive(timeout=5), 'new conn sync')

    def test_send(self):
        for data in range(90, 100):
            self.key.send(data)

        self.key.send_now('sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual(self.queue.receive(timeout=5), 'sync')

        # Messages get sent on commit
        transaction.commit()
        for data in range(90, 100):
            self.assertEqual(self.queue.receive(), data)

        # There are no more messages. They have all been consumed.
        self.key.send_now('sync')
        self.assertEqual(self.queue.receive(timeout=5), 'sync')

    def test_abort(self):
        for data in range(90, 100):
            self.key.send(data)

        self.key.send_now('sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual(self.queue.receive(timeout=5), 'sync')

        # Messages get forgotten on abort.
        transaction.abort()

        # There are no more messages. They have all been consumed.
        self.key.send_now('sync2')
        self.assertEqual(self.queue.receive(timeout=5), 'sync2')
