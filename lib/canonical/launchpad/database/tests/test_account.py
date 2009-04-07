# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = []

from textwrap import dedent
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config

from canonical.launchpad.database.account import Account
from canonical.launchpad.ftests import login
from canonical.launchpad.interfaces.account import IAccountSet
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.dbpolicy import SlaveDatabasePolicy
from canonical.launchpad.webapp.interfaces import (
    AUTH_STORE, IStoreSelector, SLAVE_FLAVOR)
from canonical.testing.layers import DatabaseFunctionalLayer


class TestAccountSetRetriesWhenAccountNotFound(TestCaseWithFactory):
    """Methods of IAccountSet that fetch accounts will retry using the master
    database if the object is not found when using the default one.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.account = self.factory.makeAccount('Test account')
        login(removeSecurityProxy(self.account.preferredemail).email)
        config_overlay = dedent("""
            [database]
            auth_slave: dbname=launchpad_empty
            """)
        config.push('empty_slave', config_overlay)
        self._assertSlaveDBIsEmpty()
        getUtility(IStoreSelector).push(SlaveDatabasePolicy())
        self.account_set = getUtility(IAccountSet)

    def tearDown(self):
        TestCaseWithFactory.tearDown(self)
        getUtility(IStoreSelector).pop()
        config.pop('empty_slave')

    def _assertSlaveDBIsEmpty(self):
        slave_store = getUtility(IStoreSelector).get(
            AUTH_STORE, SLAVE_FLAVOR)
        self.assertEqual(slave_store.find(Account).count(), 0)

    def test_get(self):
        self.assertIsNot(self.account_set.get(self.account.id), None)

    def test_getByOpenIDIdentifier(self):
        self.assertIsNot(
            self.account_set.getByOpenIDIdentifier(
                self.account.openid_identifier),
            None)

    def test_getByEmail(self):
        self.assertIsNot(
            self.account_set.getByEmail(self.account.preferredemail.email),
            None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
