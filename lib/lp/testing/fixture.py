# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad test fixtures that have no better home."""

__metaclass__ = type
__all__ = [
    'ZopeEventHandlerFixture',
    ]

from fixtures import Fixture
from zope.component import (
    getGlobalSiteManager,
    provideHandler,
    )


class ZopeEventHandlerFixture(Fixture):
    """A fixture that provides and then unprovides a Zope event handler."""

    def __init__(self, handler):
        super(ZopeEventHandlerFixture, self).__init__()
        self._handler = handler

    def setUp(self):
        super(ZopeEventHandlerFixture, self).setUp()
        gsm = getGlobalSiteManager()
        provideHandler(self._handler)
        self.addCleanup(gsm.unregisterHandler, self._handler)
