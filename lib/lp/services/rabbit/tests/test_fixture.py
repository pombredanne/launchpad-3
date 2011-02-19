# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Rabbit fixture."""

__metaclass__ = type

import socket

from amqplib import client_0_8 as amqp

from lp.testing import TestCase
from lp.services.rabbit.testing.server import RabbitServer


class TestRabbitFixture(TestCase):

    def test_start_check_shutdown(self):
        fixture = RabbitServer()
        try:
            fixture.setUp()
            # We can connect.
            host = 'localhost:%s' % fixture.config.port
            conn = amqp.Connection(host=host, userid="guest",
                password="guest", virtual_host="/", insist=False)
            conn.close()
            # And get a log file
            log = fixture.getDetails()['log']
            # Which shouldn't blow up on iteration.
            list(log.iter_text())
        finally:
            fixture.cleanUp()
        # The daemon should be closed now.
        self.assertRaises(socket.error, amqp.Connection, host=host,
            userid="guest", password="guest", virtual_host="/", insist=False)
