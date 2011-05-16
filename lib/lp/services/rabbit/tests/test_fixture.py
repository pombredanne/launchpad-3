# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Rabbit fixture."""

__metaclass__ = type

import socket
from textwrap import dedent

from amqplib import client_0_8 as amqp
from fixtures import EnvironmentVariableFixture

from lp.testing import TestCase
from lp.services.rabbit.testing.server import RabbitServer


class TestRabbitFixture(TestCase):

    def test_start_check_shutdown(self):
        # Rabbit needs to fully isolate itself: an existing per user
        # .erlange.cookie has to be ignored, and ditto bogus HOME if other
        # tests fail to cleanup.
        self.useFixture(EnvironmentVariableFixture('HOME', '/nonsense/value'))
        fixture = RabbitServer()
        try:
            # Workaround failures-in-setup-not-attaching-details (if they did
            # we could use self.useFixture).
            self.addCleanup(self._gather_details, fixture.getDetails)
            fixture.setUp()
            # We can connect.
            host = fixture.host
            conn = amqp.Connection(host=host, userid="guest",
            password="guest", virtual_host="/", insist=False)
            conn.close()
            # And get a log file
            log = fixture.getDetails()['rabbit log file']
            # Which shouldn't blow up on iteration.
            list(log.iter_text())
            # There is a (launchpad specific) config fixture. (This could be a
            # separate class if we make the fixture external in the future).
            expected = dedent("""\
                [rabbitmq]
                host: %s
                userid: guest
                password: guest
                virtual_host: /
                """ % host)
            self.assertEqual(expected, fixture.config.service_config)

        finally:
            fixture.cleanUp()
        # The daemon should be closed now.
        self.assertRaises(socket.error, amqp.Connection, host=host,
            userid="guest", password="guest", virtual_host="/", insist=False)
