# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging utility tests."""

__metaclass__ = type

import transaction

from canonical.testing.layers import RabbitMQLayer
from lp.services.messaging.interfaces import IMessageQueue
from lp.services.messaging.queue import RabbitQueue
from lp.testing import TestCase


class TestRabbitQueue(TestCase):
    layer = RabbitMQLayer

    def setUp(self):
        super(TestCase, self).setUp()
        self.queue = RabbitQueue('whatever')

    def tearDown(self):
        if hasattr(self.queue.class_locals, 'rabbit_connection'):
            self.queue.class_locals.rabbit_connection.close()
            del self.queue.class_locals.rabbit_connection
        super(TestCase, self).tearDown()

    def test_implements(self):
        IMessageQueue.providedBy(self.queue)

    def test_send_now(self):
        queue = RabbitQueue('arbitary_queue_name')
        key = 'arbitrary.routing.key'
        queue.subscribe(key)
        for data in range(50, 60):
            queue.send_now(key, data)
            received_data = queue.receive(blocking=True)
            self.assertEqual(received_data, data)

    def test_send_now_not_backwards(self):
        queue = RabbitQueue('arbitary_queue_name')
        key = 'arbitrary.routing.key'
        queue.subscribe(key)
        for data in range(1, 10):
            queue.send_now(key, data)
        for data in range(1, 10):
            received_data = queue.receive(blocking=True)
            self.assertEqual(received_data, data)

    def test_send(self):
        queue = RabbitQueue('arbitary_queue_name')
        key = 'arbitrary.routing.key'
        queue.subscribe(key)

        for data in range(90, 100):
            queue.send(key, data)

        queue.send_now(key, 'sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual(queue.receive(), 'sync')

        # Messages get sent on commit
        transaction.commit()
        for data in range(1, 10):
            self.assertEqual(queue.receive(), data)
