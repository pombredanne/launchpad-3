# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test-specific Twisted utilities."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TReqFixture',
    ]

from fixtures import Fixture
from treq.client import HTTPClient
from twisted.web.client import (
    Agent,
    HTTPConnectionPool,
    )


class TReqFixture(Fixture):
    """A `treq` client that handles test cleanup."""

    def __init__(self, reactor, pool=None):
        super(TReqFixture, self).__init__()
        self.reactor = reactor
        if pool is None:
            pool = HTTPConnectionPool(reactor, persistent=False)
        self.pool = pool

    def _setUp(self):
        self.client = HTTPClient(Agent(self.reactor, pool=self.pool))
        self.addCleanup(self.pool.closeCachedConnections)
