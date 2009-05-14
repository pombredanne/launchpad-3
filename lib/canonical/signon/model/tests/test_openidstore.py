# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Tests for the OpenID Provider's `OpenIDStore` implementation."""

__metaclass__ = type

import time
import unittest

from openid.association import Association
from zope.component import getUtility

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.dbpolicy import SSODatabasePolicy
from canonical.launchpad.webapp.interfaces import IStoreSelector
from canonical.signon.interfaces.openidstore import IProviderOpenIDStore
from canonical.signon.model.openidstore import (
    DatabaseAssociation, ProviderOpenIDStore)
from canonical.testing import DatabaseFunctionalLayer
from lp.testing import TestCase


class ProviderOpenIDStoreTests(TestCase):
    """Tests for the `ProviderOpenIDStore` utility."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(ProviderOpenIDStoreTests, self).setUp()
        getUtility(IStoreSelector).push(SSODatabasePolicy())

    def tearDown(self):
        getUtility(IStoreSelector).pop()
        super(ProviderOpenIDStoreTests, self).tearDown()

    def test_utility(self):
        openid_store = getUtility(IProviderOpenIDStore)
        self.assertIsInstance(openid_store, ProviderOpenIDStore)

    def test_storeAssociation(self):
        openid_store = getUtility(IProviderOpenIDStore)
        openid_store.storeAssociation('server-url\xC2\xA9', Association(
                'handle', 'secret', 42, 600, 'HMAC-SHA1'))
        db_assoc = IMasterStore(DatabaseAssociation).get(
            DatabaseAssociation, (u'server-url\xA9', u'handle'))
        self.assertEquals(db_assoc.server_url, u'server-url\xA9')
        self.assertEquals(db_assoc.handle, u'handle')
        self.assertEquals(db_assoc.secret, 'secret')
        self.assertEquals(db_assoc.issued, 42)
        self.assertEquals(db_assoc.lifetime, 600)
        self.assertEquals(db_assoc.assoc_type, u'HMAC-SHA1')

    def test_getAssociation(self):
        openid_store = getUtility(IProviderOpenIDStore)
        timestamp = int(time.time())
        openid_store.storeAssociation('server-url', Association(
                'handle', 'secret', timestamp, 600, 'HMAC-SHA1'))

        assoc = openid_store.getAssociation('server-url', 'handle')
        self.assertIsInstance(assoc, Association)
        self.assertEquals(assoc.handle, 'handle')
        self.assertEquals(assoc.secret, 'secret')
        self.assertEquals(assoc.issued, timestamp)
        self.assertEquals(assoc.lifetime, 600)
        self.assertEquals(assoc.assoc_type, 'HMAC-SHA1')

    def test_getAssociation_unknown(self):
        openid_store = getUtility(IProviderOpenIDStore)
        assoc = openid_store.getAssociation('server-url', 'unknown')
        self.assertEquals(assoc, None)

    def test_getAssociation_expired(self):
        openid_store = getUtility(IProviderOpenIDStore)
        lifetime = 600
        timestamp = int(time.time()) - 2 * lifetime
        openid_store.storeAssociation('server-url', Association(
                'handle', 'secret', timestamp, lifetime, 'HMAC-SHA1'))
        # The association is not returned because it is out of date.
        # Further more, it is removed from the database.
        assoc = openid_store.getAssociation('server-url', 'handle')
        self.assertEquals(assoc, None)

        store = IMasterStore(DatabaseAssociation)
        db_assoc = store.get(DatabaseAssociation, (u'server-url', u'handle'))
        self.assertEqual(db_assoc, None)

    def test_getAssociation_no_handle(self):
        openid_store = getUtility(IProviderOpenIDStore)
        timestamp = int(time.time())
        openid_store.storeAssociation('server-url', Association(
                'handle1', 'secret', timestamp, 600, 'HMAC-SHA1'))
        openid_store.storeAssociation('server-url', Association(
                'handle2', 'secret', timestamp + 1, 600, 'HMAC-SHA1'))

        # The most recent handle is returned.
        assoc = openid_store.getAssociation('server-url', None)
        self.assertNotEqual(assoc, None)
        self.assertEqual(assoc.handle, 'handle2')

    def test_removeAssociation(self):
        openid_store = getUtility(IProviderOpenIDStore)
        self.assertEquals(
            openid_store.removeAssociation('server-url', 'unknown'), False)

        timestamp = int(time.time())
        openid_store.storeAssociation('server-url', Association(
                'handle', 'secret', timestamp, 600, 'HMAC-SHA1'))
        self.assertEquals(
            openid_store.removeAssociation('server-url', 'handle'), True)
        self.assertEquals(
            openid_store.getAssociation('server-url', 'handle'), None)

    def test_useNonce(self):
        # OpenID Providers do not need to keep track of nonces, so the
        # nonce handling method remains unimplemented.
        openid_store = getUtility(IProviderOpenIDStore)
        self.assertRaises(NotImplementedError, openid_store.useNonce,
                          'server-url', 42, 'salt')

    def test_cleanupNonces(self):
        # As we don't track nonces, there is never any nonces to clean up.
        openid_store = getUtility(IProviderOpenIDStore)
        self.assertEqual(openid_store.cleanupNonces(), 0)

    def test_cleanupAssociations(self):
        openid_store = getUtility(IProviderOpenIDStore)
        timestamp = int(time.time()) - 100
        openid_store.storeAssociation('server-url', Association(
                'handle1', 'secret', timestamp, 50, 'HMAC-SHA1'))
        openid_store.storeAssociation('server-url', Association(
                'handle2', 'secret', timestamp, 200, 'HMAC-SHA1'))

        self.assertEquals(openid_store.cleanupAssociations(), 1)

        # The second (non-expired) association is left behind.
        self.assertNotEqual(
            openid_store.getAssociation('server-url', 'handle2'), None)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

