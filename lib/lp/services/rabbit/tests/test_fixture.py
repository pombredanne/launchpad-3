# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Rabbit fixture."""

__metaclass__ = type

import itertools
import socket
from textwrap import dedent

from amqplib import client_0_8 as amqp
from fixtures import EnvironmentVariableFixture
from testtools.content import Content

from lp.services.rabbit.testing.server import RabbitServer
from lp.testing import TestCase

#
# copy_content() and gather_details() have been copied from
# lp:~allenap/testtools/gather-details. If/when that branch lands the copies
# here should be removed.
#


def copy_content(content_object):
    """Make a copy of the given content object.

    The content within `content_object` is iterated and saved. This is useful
    when the source of the content is volatile, a log file in a temporary
    directory for example.

    :param content_object: A `content.Content` instance.
    :return: A `content.Content` instance with the same mime-type as
        `content_object` and a non-volatile copy of its content.
    """
    content_bytes = list(content_object.iter_bytes())
    content_callback = lambda: content_bytes
    return Content(content_object.content_type, content_callback)


def gather_details(source, target):
    """Merge the details from `source` into `target`.

    :param source: A *detailed* object from which details will be gathered.
    :param target: A *detailed* object into which details will be gathered.
    """
    source_details = source.getDetails()
    target_details = target.getDetails()
    for name, content_object in source_details.items():
        new_name = name
        disambiguator = itertools.count(1)
        while new_name in target_details:
            new_name = '%s-%d' % (name, next(disambiguator))
        name = new_name
        target.addDetail(name, copy_content(content_object))


class TestRabbitFixture(TestCase):

    def test_start_check_shutdown(self):
        # Rabbit needs to fully isolate itself: an existing per user
        # .erlange.cookie has to be ignored, and ditto bogus HOME if other
        # tests fail to cleanup.
        self.useFixture(EnvironmentVariableFixture('HOME', '/nonsense/value'))

        fixture = RabbitServer()

        try:
            with fixture:
                # We can connect.
                connect_arguments = {
                    "host": 'localhost:%s' % fixture.config.port,
                    "userid": "guest", "password": "guest",
                    "virtual_host": "/", "insist": False,
                    }
                amqp.Connection(**connect_arguments).close()
                # And get a log file.
                log = fixture.runner.getDetails()["rabbit.log"]
                # Which shouldn't blow up on iteration.
                list(log.iter_text())

            # There is a (launchpad specific) config fixture. (This could be a
            # separate class if we make the fixture external in the future).
            expected = dedent("""\
                [rabbitmq]
                host: localhost:%d
                userid: guest
                password: guest
                virtual_host: /
                """ % fixture.config.port)
            self.assertEqual(expected, fixture.config.service_config)

        except:
            # Work around failures-in-setup-not-attaching-details (if they did
            # we could use self.useFixture).
            gather_details(fixture.runner.environment, fixture.runner)
            gather_details(fixture.runner, fixture)
            gather_details(fixture.config, fixture)
            gather_details(fixture, self)
            raise

        # The daemon should be closed now.
        self.assertRaises(socket.error, amqp.Connection, **connect_arguments)
