# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the DBPolicy."""

__metaclass__ = type
__all__ = []

from lazr.restful.interfaces import IWebServiceConfiguration
from zope.component import (
    getAdapter,
    getUtility,
    )
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.security.management import (
    endInteraction,
    newInteraction,
    )
from zope.session.interfaces import (
    IClientIdManager,
    ISession,
    )

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    ISlaveStore,
    )
from canonical.launchpad.layers import (
    FeedsLayer,
    setFirstLayer,
    WebServiceLayer,
    )
from canonical.launchpad.tests.readonly import (
    remove_read_only_file,
    touch_read_only_file,
    )
from canonical.launchpad.webapp.dbpolicy import (
    BaseDatabasePolicy,
    LaunchpadDatabasePolicy,
    MasterDatabasePolicy,
    ReadOnlyLaunchpadDatabasePolicy,
    SlaveDatabasePolicy,
    SlaveOnlyDatabasePolicy,
    )
from canonical.launchpad.webapp.interfaces import (
    ALL_STORES,
    DEFAULT_FLAVOR,
    DisallowedStore,
    IDatabasePolicy,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    ReadOnlyModeDisallowedStore,
    SLAVE_FLAVOR,
    )
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import (
    DatabaseFunctionalLayer,
    FunctionalLayer,
    )
from lp.testing import TestCase


class ImplicitDatabasePolicyTestCase(TestCase):
    """Tests for when there is no policy installed."""
    layer = DatabaseFunctionalLayer

    def test_defaults(self):
        for store in ALL_STORES:
            self.assertProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                IMasterStore)

    def test_dbusers(self):
        store_selector = getUtility(IStoreSelector)
        main_store = store_selector.get(MAIN_STORE, DEFAULT_FLAVOR)
        self.failUnlessEqual(self.getDBUser(main_store), 'launchpad_main')

    def getDBUser(self, store):
        return store.execute(
            'SHOW session_authorization').get_one()[0]


class BaseDatabasePolicyTestCase(ImplicitDatabasePolicyTestCase):
    """Base tests for DatabasePolicy implementation."""

    policy = None

    def setUp(self):
        super(BaseDatabasePolicyTestCase, self).setUp()
        if self.policy is None:
            self.policy = BaseDatabasePolicy()
        getUtility(IStoreSelector).push(self.policy)

    def tearDown(self):
        getUtility(IStoreSelector).pop()
        super(BaseDatabasePolicyTestCase, self).tearDown()

    def test_correctly_implements_IDatabasePolicy(self):
        self.assertProvides(self.policy, IDatabasePolicy)


class SlaveDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def setUp(self):
        if self.policy is None:
            self.policy = SlaveDatabasePolicy()
        super(SlaveDatabasePolicyTestCase, self).setUp()

    def test_defaults(self):
        for store in ALL_STORES:
            self.assertProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                ISlaveStore)

    def test_master_allowed(self):
        for store in ALL_STORES:
            self.assertProvides(
                getUtility(IStoreSelector).get(store, MASTER_FLAVOR),
                IMasterStore)


class SlaveOnlyDatabasePolicyTestCase(SlaveDatabasePolicyTestCase):
    """Tests for the `SlaveDatabasePolicy`."""

    def setUp(self):
        self.policy = SlaveOnlyDatabasePolicy()
        super(SlaveOnlyDatabasePolicyTestCase, self).setUp()

    def test_master_allowed(self):
        for store in ALL_STORES:
            self.failUnlessRaises(
                DisallowedStore,
                getUtility(IStoreSelector).get, store, MASTER_FLAVOR)


class MasterDatabasePolicyTestCase(BaseDatabasePolicyTestCase):
    """Tests for the `MasterDatabasePolicy`."""

    def setUp(self):
        self.policy = MasterDatabasePolicy()
        super(MasterDatabasePolicyTestCase, self).setUp()

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
            self.assertProvides(
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
        super(LaunchpadDatabasePolicyTestCase, self).setUp()


class LayerDatabasePolicyTestCase(TestCase):
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
        api_prefix = getUtility(
            IWebServiceConfiguration).active_versions[0]
        server_url = 'http://api.launchpad.dev/%s' % api_prefix
        request = LaunchpadTestRequest(SERVER_URL=server_url)
        setFirstLayer(request, WebServiceLayer)
        policy = IDatabasePolicy(request)
        self.assertIsInstance(policy, MasterDatabasePolicy)

    def test_WebServiceRequest_uses_LaunchpadDatabasePolicy(self):
        """WebService requests with a session cookie will use the
        standard LaunchpadDatabasePolicy so their database queries
        can be outsourced to a slave database when possible.
        """
        api_prefix = getUtility(
            IWebServiceConfiguration).active_versions[0]
        server_url = 'http://api.launchpad.dev/%s' % api_prefix
        request = LaunchpadTestRequest(SERVER_URL=server_url)
        newInteraction(request)
        try:
            # First, generate a valid session cookie.
            cookie_name = getUtility(IClientIdManager).namespace
            ISession(request)['whatever']['whatever'] = 'whatever'
            # Then stuff it into the request where we expect to
            # find it. The database policy is only interested if
            # a session cookie was sent with the request, not it
            # one has subsequently been set in the response.
            request._cookies = request.response._cookies
            setFirstLayer(request, WebServiceLayer)
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, LaunchpadDatabasePolicy)
        finally:
            endInteraction()

    def test_WebServiceRequest_uses_ReadOnlyDatabasePolicy(self):
        """WebService requests should use the read only database
        policy in read only mode.
        """
        touch_read_only_file()
        try:
            api_prefix = getUtility(
                IWebServiceConfiguration).active_versions[0]
            server_url = 'http://api.launchpad.dev/%s' % api_prefix
            request = LaunchpadTestRequest(SERVER_URL=server_url)
            setFirstLayer(request, WebServiceLayer)
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, ReadOnlyLaunchpadDatabasePolicy)
        finally:
            remove_read_only_file()

    def test_read_only_mode_uses_ReadOnlyLaunchpadDatabasePolicy(self):
        touch_read_only_file()
        try:
            request = LaunchpadTestRequest(
                SERVER_URL='http://launchpad.dev')
            policy = IDatabasePolicy(request)
            self.assertIsInstance(policy, ReadOnlyLaunchpadDatabasePolicy)
        finally:
            remove_read_only_file()

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
        super(ReadOnlyLaunchpadDatabasePolicyTestCase, self).setUp()

    def test_defaults(self):
        # default Store is the slave.
        for store in ALL_STORES:
            self.assertProvides(
                getUtility(IStoreSelector).get(store, DEFAULT_FLAVOR),
                ISlaveStore)

    def test_slave_allowed(self):
        for store in ALL_STORES:
            self.assertProvides(
                getUtility(IStoreSelector).get(store, SLAVE_FLAVOR),
                ISlaveStore)

    def test_master_disallowed(self):
        store_selector = getUtility(IStoreSelector)
        for store in ALL_STORES:
            self.assertRaises(
                ReadOnlyModeDisallowedStore,
                store_selector.get, store, MASTER_FLAVOR)
