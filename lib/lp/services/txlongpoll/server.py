# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""TxLongPoll server fixture."""

__metaclass__ = type
__all__ = [
    'TxLongPollServer',
    ]

from textwrap import dedent

from txlongpollfixture.server import TxLongPollFixture
from rabbitfixture.server import RabbitServer


class TxLongPollServer(TxLongPollFixture):
    """A TxLongPoll server fixture with Launchpad-specific config.

    :ivar service_config: A snippet of .ini that describes the `txlongpoll`
        configuration.
    """

    def setUp(self):
        super(TxLongPollServer, self).setUp()
        self.rabbitserver = RabbitServer()
        self.useFixture(self.rabbitserver)
        self.config['service_config'] = dedent("""\
            [rabbitmq]
            host: localhost:%d
            userid: guest
            password: guest
            virtual_host: /

            [txlongpoll]
            frontend_port: %d
            """ % (
                self.rabbitserver.config.port,
                self.config['frontend_port']))
