# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the `IOpenIDConsumerStore` utility."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.database.tests.test_baseopenidstore import (
    BaseStormOpenIDStoreTestsMixin,
    )
from canonical.launchpad.interfaces.openidconsumer import IOpenIDConsumerStore
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCase


class OpenIDConsumerStoreTests(BaseStormOpenIDStoreTestsMixin, TestCase):
    """Tests for the `IOpenIDConsumerStore` utility."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(OpenIDConsumerStoreTests, self).setUp()
        self.store = getUtility(IOpenIDConsumerStore)
