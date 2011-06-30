# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""An API for messaging systems in Launchpad, e.g. RabbitMQ."""

__metaclass__ = type
__all__ = []


from amqplib import client_0_8 as amqp
import transaction
from threading import local as thread_local

from canonical.config import config

LAUNCHPAD_EXCHANGE = "launchpad-exchange"


class MessagingDataManager:
    def __init__(self, messaging_utility):
        self.utility = messaging_utility

    def _cleanup(self):
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
        return None

    def commit(self, txn):
        for message in self.utility.locals.messages:
            self.utility.send_now(**message)
        self._cleanup()


class Messaging:

    locals = thread_local()

    def initialize(self):
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

    def send(self, routing_key, json_data=None, pickle=None, oncommit=True):
        """XXX"""
        if pickle is not None:
            raise AssertionError("pickle param not implemented yet")

        self.initalize()
        msg = amqp.Message(json_data)

        if not oncommit:
            self.send_now(routing_key, json_data)
            return

        if not hasattr(self.locals, "messages"):
            self.locals.messages = []
            txn = transaction.get()
            txn.join(MessagingDataManager())

        self.locals.messages.append(
            dict(routing_key=routing_key, json_data=json_data))


    def send_now(self, routing_key, json_data=None, pickle=None):
        channel = self.locals.rabbit.channel()
        channel.basic_publish(
            exchange=LAUNCHPAD_EXCHANGE,
            routing_key=routing_key,
            msg=amqp.Message(json_data)
            )

    def receive(self, queue_name, blocking=True):
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


messaging = Messaging()
