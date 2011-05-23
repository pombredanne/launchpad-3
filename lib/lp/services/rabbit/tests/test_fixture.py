# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Rabbit fixture."""

__metaclass__ = type

import socket

from amqplib import client_0_8 as amqp
from fixtures import EnvironmentVariableFixture

from lp.services.rabbit.testing.server import RabbitServer
from lp.testing import TestCase


class TestRabbitFixture(TestCase):

    def test_start_check_shutdown(self):
        # Rabbit needs to fully isolate itself: an existing per user
        # .erlange.cookie has to be ignored, and ditto bogus HOME if other
        # tests fail to cleanup.
        self.useFixture(EnvironmentVariableFixture('HOME', '/nonsense/value'))

        fixture = RabbitServer()

        def get_fixture_details():
            fixture_getters = (
                lambda: fixture,
                lambda: fixture.config,
                lambda: fixture.runner,
                lambda: fixture.runner.server)
            for get_fixture in fixture_getters:
                try:
                    fx = get_fixture()
                except AttributeError:
                    continue
                else:
                    self._gather_details(fx.getDetails)

        # Work around two issues: (1) failures in setup don't attach details
        # (if they did we could use self.useFixture), and (2) failures in
        # sub-fixtures don't propagate up.
        self.addCleanup(get_fixture_details)

        with fixture:
            # We can connect.
            connect_arguments = {
                "host": 'localhost:%s' % fixture.config.port,
                "userid": "guest", "password": "guest",
                "virtual_host": "/", "insist": False,
                }
            amqp.Connection(**connect_arguments).close()
            # And get a log file
            log = fixture.runner.getDetails()['rabbit log file']
            # Which shouldn't blow up on iteration.
            list(log.iter_text())

        # The daemon should be closed now.
        self.assertRaises(socket.error, amqp.Connection, **connect_arguments)
