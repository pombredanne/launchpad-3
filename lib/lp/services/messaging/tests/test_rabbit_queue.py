# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Messaging utility tests."""

__metaclass__ = type

from canonical.testing.layers import RabbitMQLayer
from lp.testing import TestCase

from lp.services.messaging.interfaces import IMessageQueue
from lp.services.messaging.queue import RabbitQueue


class TestRabbitQueue(TestCase):
    layer = RabbitMQLayer

    def test_implements(self):
        queue = RabbitQueue('whatever')
        IMessageQueue.providedBy(queue)

    def test_send_now(self):
        queue = RabbitQueue('arbitary_queue_name')
        key = 'arbitrary.routing.key'
        queue.subscribe(key)
        for data in range(1, 10):
            queue.send_now(key, data)
        # XXX: WTF are they backwards
        for date in range(9, 0):
            received_data = queue.receive(blocking=True)
            self.assertEqual(received_data, data)

    def test_send(self):
        queue = RabbitQueue('arbitary_queue_name')
        key = 'arbitrary.routing.key'

        for data in range(1, 10):
            queue.send(key, data)

        queue.send_now(key, 'sync')
        # There is nothing in the queue except the sync we just sent.
        self.assertEqual(queue.receive(), 'sync')

        # Messages get sent on commit
        transaction.commit()
        for data in range(1, 10):
            self.assertEqual(queue.receive(), data)
