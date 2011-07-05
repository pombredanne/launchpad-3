# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.testing.fixture."""

__metaclass__ = type

from textwrap import dedent

from fixtures import EnvironmentVariableFixture

from canonical.testing.layers import BaseLayer
from lp.services.rabbit.server import RabbitServer
from lp.testing import TestCase


class TestRabbitServer(TestCase):

    layer = BaseLayer

    def test_service_config(self):
        # Rabbit needs to fully isolate itself: an existing per user
        # .erlang.cookie has to be ignored, and ditto bogus HOME if other
        # tests fail to cleanup.
        self.useFixture(EnvironmentVariableFixture('HOME', '/nonsense/value'))

        # RabbitServer pokes some .ini configuration into its config.
        fixture = self.useFixture(RabbitServer())
        expected = dedent("""\
            [rabbitmq]
            host: localhost:%d
            userid: guest
            password: guest
            virtual_host: /
            """ % fixture.config.port)
        self.assertEqual(expected, fixture.config.service_config)
