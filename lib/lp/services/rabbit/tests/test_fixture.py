# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Rabbit fixture."""

__metaclass__ = type

import socket

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
        try:
            # Workaround failures-in-setup-not-attaching-details (if they did
            # we could use self.useFixture).
            self.addCleanup(self._gather_details, fixture.getDetails)
            fixture.setUp()
            # We can connect.
            fixture.getConnection().close()
            # And get a log file
            log = fixture.getDetails()['rabbit log file']
            # Which shouldn't blow up on iteration.
            list(log.iter_text())
        finally:
            fixture.cleanUp()
        # The daemon should be closed now.
        self.assertRaises(socket.error, fixture.getConnection)
