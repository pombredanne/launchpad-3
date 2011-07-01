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
    RabbitQueue,
    RabbitRoutingKey,
    )
from lp.testing import TestCase


class TestRabbitQueue(TestCase):
    layer = RabbitMQLayer

    def setUp(self):
        super(TestCase, self).setUp()
        self.queue_name = 'whatever'
        self.queue = RabbitQueue(self.queue_name)
        self.key = RabbitRoutingKey('arbitrary.routing.key')
        self.key.associateConsumer(self.queue)

    def tearDown(self):
        self.queue._disconnect()
        super(TestCase, self).tearDown()

    def test_implements(self):
        self.assertTrue(IMessageConsumer.providedBy(self.queue))
        self.assertTrue(IMessageProducer.providedBy(self.key))

    def test_send_now(self):
        for data in range(50, 60):
            self.key.send_now(data)
            received_data = self.queue.receive(timeout=5)
            self.assertEqual(received_data, data)

    def test_send_now_not_backwards(self):
        for data in range(1, 10):
            self.queue.send_now(self.key, data)
        for data in range(1, 10):
            received_data = self.queue.receive(blocking=True)
            self.assertEqual(received_data, data)

    def test_receive_consumes(self):
        for data in range(55, 65):
            self.queue.send_now(self.key, data)
            self.assertEqual(self.queue.receive(blocking=True), data)

        # None of the messages we received where put back. They were all
        # consumed.
        self.assertRaises(
            EmptyQueueException,
            self.queue.receive, blocking=False)

        # New connections to the queue see an empty queue too.
        self.queue._disconnect()
        queue = RabbitQueue(self.queue_name)
        queue.subscribe(self.key)
        queue.send(self.key, 'new conn sync')
        self.assertEqual(queue.receive(blocking=True), 'new conn sync')

    def test_send(self):
        for data in range(90, 100):
            self.queue.send(key, data)

        self.queue.send_now(key, 'sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual(self.queue.receive(), 'sync')

        # Messages get sent on commit
        transaction.commit()
        for data in range(90, 100):
            self.assertEqual(self.queue.receive(), data)

        # There are no more messages. They have all been consumed.
        self.queue.send_now(key, 'sync')
        self.assertEqual(self.queue.receive(), 'sync')
