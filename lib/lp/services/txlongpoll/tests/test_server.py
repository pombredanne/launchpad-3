# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.rabbit.TxLongPollServer."""

__metaclass__ = type

from ConfigParser import SafeConfigParser
from StringIO import StringIO

from canonical.config import config
from canonical.testing.layers import RabbitMQLayer
from lp.services.txlongpoll.server import TxLongPollServer
from lp.testing import TestCase


class TestTxLongPollServer(TestCase):

    layer = RabbitMQLayer

    def test_service_config(self):
        # TxLongPollServer pokes some .ini configuration into its config.
        fixture = self.useFixture(TxLongPollServer(
            broker_user='guest', broker_password='guest', broker_vhost='/',
            broker_port=123, frontend_port=None))
        service_config = SafeConfigParser()
        service_config.readfp(StringIO(fixture.config['service_config']))
        self.assertEqual(
            ["rabbitmq", "txlongpoll"], sorted(service_config.sections()))
        # txlongpoll section
        expected = {
            "frontend_port": "%d" % fixture.config['frontend_port'],
            }
        observed = dict(service_config.items("txlongpoll"))
        self.assertEqual(expected, observed)
        # rabbitmq section
        expected = {
            "host": "%s" % (
                config.rabbitmq.host),
            "password": "guest",
            "userid": "guest",
            "virtual_host": "/",
            }
        observed = dict(service_config.items("rabbitmq"))
        self.assertEqual(expected, observed)
