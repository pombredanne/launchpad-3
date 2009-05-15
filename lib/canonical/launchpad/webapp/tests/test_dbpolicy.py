# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for the DBPolicy."""

__metaclass__ = type
__all__ = []

import unittest

from zope.component import getAdapter, getUtility
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest

from canonical.config import config
from canonical.launchpad.interfaces import IMasterStore, ISlaveStore
from canonical.launchpad.layers import (
    FeedsLayer, setFirstLayer, WebServiceLayer)
from canonical.signon.layers import IdLayer, OpenIDLayer
from lp.testing import TestCase
from canonical.launchpad.webapp.dbpolicy import (
    BaseDatabasePolicy, LaunchpadDatabasePolicy, MasterDatabasePolicy,
    ReadOnlyLaunchpadDatabasePolicy, SlaveDatabasePolicy,
    SlaveOnlyDatabasePolicy, SSODatabasePolicy)
from canonical.launchpad.webapp.interfaces import (
    ALL_STORES, AUTH_STORE, DEFAULT_FLAVOR, DisallowedStore, IDatabasePolicy,
    IStoreSelector, MAIN_STORE, MASTER_FLAVOR, ReadOnlyModeDisallowedStore,
    SLAVE_FLAVOR)
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.launchpad.webapp.tests import DummyConfigurationTestCase
from canonical.testing.layers import DatabaseFunctionalLayer, FunctionalLayer


class ImplicitDatabasePolicyTestCase(TestCase):
    """Tests for when there is no policy installed."""
    layer = DatabaseFunctionalLayer

    def test_defaults(self):
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                IMasterStore)

    def test_dbusers(self):
        store_selector = getUtility(IStoreSelector)
        main_store = store_selector.get(MAIN_STORE, DEFAULT_FLAVOR)
        self.failUnlessEqual(self.getDBUser(main_store), 'launchpad_main')

        auth_store = store_selector.get(AUTH_STORE, DEFAULT_FLAVOR)
        self.failUnlessEqual(self.getDBUser(auth_store), 'launchpad_auth')

    def getDBUser(self, store):
        return store.execute(
            'SHOW session_authorization').get_one()[0]


class BaseDatabasePolicyTestCase(ImplicitDatabasePolicyTestCase):
    """Base tests for DatabasePolicy implementation."""

    policy = None

    def setUp(self):
        if self.policy is None:
            self.policy = BaseDatabasePolicy()
        getUtility(IStoreSelector).push(self.policy)

    def tearDown(self):
        getUtility(IStoreSelector).pop()

    def test_correctly_implements_IDatabasePolicy(self):
        self.assertCorrectlyProvides(self.policy, IDatabasePolicy)


class SlaveDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def setUp(self):
        if self.policy is None:
            self.policy = SlaveDatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_defaults(self):
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                ISlaveStore)

    def test_master_allowed(self):
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, MASTER_FLAVOR),
                IMasterStore)


class SlaveOnlyDatabasePolicyTestCase(SlaveDatabasePolicyTestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def setUp(self):
        self.policy = SlaveOnlyDatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_master_allowed(self):
        for store in ALL_STORES:
            self.failUnlessRaises(
                DisallowedStore,
                getUtility(IStoreSelector).get, store, MASTER_FLAVOR)


class MasterDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `MasterDatabasePolicy`."""

    def setUp(self):
        self.policy = MasterDatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_XMLRPCRequest_uses_MasterPolicy(self):
        """XMLRPC should always use the master flavor, since they always
        use POST and do not support session cookies.
        """
        request = LaunchpadTestRequest(
            SERVER_URL='http://xmlrpc-private.launchpad.dev')
        setFirstLayer(request, IXMLRPCRequest)
        policy = getAdapter(request, IDatabasePolicy)
        self.failUnless(
            isinstance(policy, MasterDatabasePolicy),
            "Expected MasterDatabasePolicy, not %s." % policy)

    def test_slave_allowed(self):
        # We get the master store even if the slave was requested.
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, SLAVE_FLAVOR),
                ISlaveStore)


class LaunchpadDatabasePolicyTestCase(SlaveDatabasePolicyTestCase):
    """Fuller LaunchpadDatabasePolicy tests are in the page tests.

    This test just checks the defaults, which is the same as the
    slave policy for unauthenticated requests.
    """
    def setUp(self):
        request = LaunchpadTestRequest(SERVER_URL='http://launchpad.dev')
        self.policy = LaunchpadDatabasePolicy(request)
        SlaveDatabasePolicyTestCase.setUp(self)


class SSODatabasePolicyTestCase(BaseDatabasePolicyTestCase):

    def setUp(self):
        self.policy = SSODatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_defaults(self):
        self.assertCorrectlyProvides(
            getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR),
            ISlaveStore)
        self.assertCorrectlyProvides(
            getUtility(IStoreSelector).get(AUTH_STORE, DEFAULT_FLAVOR),
            IMasterStore)

    def test_disallowed(self):
        for store in ALL_STORES:
            if store == AUTH_STORE:
                disallowed_flavor = SLAVE_FLAVOR
            else:
                disallowed_flavor = MASTER_FLAVOR
            self.failUnlessRaises(
                DisallowedStore,
                getUtility(IStoreSelector).get, store, disallowed_flavor)

    def test_dbusers(self):
        store_selector = getUtility(IStoreSelector)
        for store in ALL_STORES:
            if store == AUTH_STORE:
                user = 'sso_auth'
            else:
                user = 'sso_main'
            self.failUnlessEqual(
                user,
                self.getDBUser(store_selector.get(store, DEFAULT_FLAVOR)))


class LayerDatabasePolicyTestCase(DummyConfigurationTestCase):
    layer = FunctionalLayer

    def test_FeedsLayer_uses_SlaveDatabasePolicy(self):
        """FeedsRequest should use the SlaveDatabasePolicy since they
        are read-only in nature. Also we don't want to send session cookies 
        over them.
        """
        request = LaunchpadTestRequest(
            SERVER_URL='http://feeds.launchpad.dev')
        setFirstLayer(request, FeedsLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, SlaveOnlyDatabasePolicy)

    def test_WebServiceRequest_uses_MasterDatabasePolicy(self):
        """WebService requests should always use the master flavor, since
        it's likely that clients won't support cookies and thus mixing read
        and write requests will result in incoherent views of the data.

        XXX 20090320 Stuart Bishop bug=297052: This doesn't scale of course
            and will meltdown when the API becomes popular.
        """
        server_url = ('http://api.launchpad.dev/'
                      + self.config.service_version_uri_prefix)
        request = LaunchpadTestRequest(SERVER_URL=server_url)
        setFirstLayer(request, WebServiceLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, MasterDatabasePolicy)

    def test_OpenIDLayer_uses_SSODatabasePolicy(self):
        request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.dev/+openid')
        setFirstLayer(request, OpenIDLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, SSODatabasePolicy)

    def test_IdLayer_uses_SSODatabasePolicy(self):
        request = LaunchpadTestRequest(
            SERVER_URL='http://openid.launchpad.dev/+openid')
        setFirstLayer(request, IdLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, SSODatabasePolicy)

    def test_read_only_mode_uses_ReadOnlyLaunchpadDatabasePolicy(self):
        config.push('read_only', """
            [launchpad]
            read_only: True""")
        try:
            request = LaunchpadTestRequest(
                SERVER_URL='http://launchpad.dev')
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, ReadOnlyLaunchpadDatabasePolicy)
        finally:
            config.pop('read_only')

    def test_read_only_mode_IdLayer_uses_SSODatabasePolicy(self):
        config.push('read_only', """
            [launchpad]
            read_only: True""")
        try:
            request = LaunchpadTestRequest(
                SERVER_URL='http://openid.launchpad.dev/+openid')
            setFirstLayer(request, IdLayer)
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, SSODatabasePolicy)
        finally:
            config.pop('read_only')

    def test_other_request_uses_LaunchpadDatabasePolicy(self):
        """By default, requests should use the LaunchpadDatabasePolicy."""
        server_url = 'http://launchpad.dev/'
        request = LaunchpadTestRequest(SERVER_URL=server_url)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, LaunchpadDatabasePolicy)


class ReadOnlyLaunchpadDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `ReadOnlyModeLaunchpadDatabasePolicy`"""

    def setUp(self):
        self.policy = ReadOnlyLaunchpadDatabasePolicy()
        BaseDatabasePolicyTestCase.setUp(self)

    def test_defaults(self):
        # default Store is the slave.
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                ISlaveStore)

    def test_slave_allowed(self):
        for store in ALL_STORES:
            self.assertCorrectlyProvides(
                getUtility(IStoreSelector).get(store, SLAVE_FLAVOR),
                ISlaveStore)

    def test_master_disallowed(self):
        store_selector = getUtility(IStoreSelector)
        for store in ALL_STORES:
            self.assertRaises(
                ReadOnlyModeDisallowedStore,
                store_selector.get, store, MASTER_FLAVOR)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
