# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.database.tests.test_baseopenidstore import (
    BaseStormOpenIDStoreTestsMixin)
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.signon.interfaces.openidstore import IProviderOpenIDStore
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCase


class ProviderOpenIDStoreTests(BaseStormOpenIDStoreTestsMixin, TestCase):
    """Tests for the `ProviderOpenIDStore` utility."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProviderOpenIDStoreTests, self).setUp()
        getUtility(IStoreSelector).push(SSODatabasePolicy())
        self.store = getUtility(IProviderOpenIDStore)

    def tearDown(self):
        getUtility(IStoreSelector).pop()
        super(ProviderOpenIDStoreTests, self).tearDown()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

