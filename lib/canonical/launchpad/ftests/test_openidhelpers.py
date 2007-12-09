# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Tests for OpenID test helpers."""

__metaclass__ = type

import os
import unittest

from openid.consumer.consumer import Consumer
from openid.consumer.discover import (
    OPENID_1_0_TYPE, OPENID_1_1_TYPE, OPENID_2_0_TYPE,
    OPENID_IDP_2_0_TYPE)
from openid.message import IDENTIFIER_SELECT
from openid.store.memstore import MemoryStore

from canonical.launchpad.ftests.openidhelpers import (
    complete_from_browser, make_endpoint, make_identifier_select_endpoint,
    maybe_fixup_identifier_select_request)
from canonical.launchpad.ftests.test_pages import (
    PageTestSuite, setUpGlobs)


class MakeEndpointTests(unittest.TestCase):
    """Tests for the make_openid() helper."""

    def test_openid10(self):
        """Test that OpenID 1.0 endpoints are constructed correctly."""
        endpoint = make_endpoint(
            OPENID_1_0_TYPE, 'http://example.com/claimed',
            'http://example.com/identity')
        self.assertEqual(endpoint.type_uris, [OPENID_1_0_TYPE])
        self.assertEqual(endpoint.claimed_id, 'http://example.com/claimed')
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, 'http://example.com/identity')

    def test_openid11(self):
        """Test that OpenID 1.1 endpoints are constructed correctly."""
        endpoint = make_endpoint(
            OPENID_1_1_TYPE, 'http://example.com/claimed',
            'http://example.com/identity')
        self.assertEqual(endpoint.type_uris, [OPENID_1_1_TYPE])
        self.assertEqual(endpoint.claimed_id, 'http://example.com/claimed')
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, 'http://example.com/identity')

    def test_openid20(self):
        """Test that OpenID 2.0 endpoints are constructed correctly."""
        endpoint = make_endpoint(
            OPENID_2_0_TYPE, 'http://example.com/claimed',
            'http://example.com/identity')
        self.assertEqual(endpoint.type_uris, [OPENID_2_0_TYPE])
        self.assertEqual(endpoint.claimed_id, 'http://example.com/claimed')
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, 'http://example.com/identity')

    def test_no_local_id(self):
        """Test that endpoints with no local ID are constructed correctly.

        In this case, the local ID is the same as the claimed ID.
        """
        endpoint = make_endpoint(
            OPENID_1_1_TYPE, 'http://example.com/claimed')
        self.assertEqual(endpoint.claimed_id, 'http://example.com/claimed')
        self.assertEqual(endpoint.local_id, 'http://example.com/claimed')


class MakeIdentifierSelectEndpointTests(unittest.TestCase):
    """Tests for the make_identifier_select_endpoint() helper."""

    def test_openid10(self):
        """Test that OpenID 1.0 endpoints are constructed correctly."""
        endpoint = make_identifier_select_endpoint(OPENID_1_0_TYPE)
        self.assertEqual(endpoint.type_uris, [OPENID_1_0_TYPE])
        self.assertEqual(endpoint.claimed_id, IDENTIFIER_SELECT)
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, IDENTIFIER_SELECT)

    def test_openid11(self):
        """Test that OpenID 1.1 endpoints are constructed correctly."""
        endpoint = make_identifier_select_endpoint(OPENID_1_1_TYPE)
        self.assertEqual(endpoint.type_uris, [OPENID_1_1_TYPE])
        self.assertEqual(endpoint.claimed_id, IDENTIFIER_SELECT)
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, IDENTIFIER_SELECT)

    def test_openid20(self):
        """Test that OpenID 2.0 endpoints are constructed correctly."""
        endpoint = make_identifier_select_endpoint(OPENID_2_0_TYPE)
        # Use the OP Identifier type URI for 2.0 requests:
        self.assertEqual(endpoint.type_uris, [OPENID_IDP_2_0_TYPE])
        self.assertEqual(endpoint.claimed_id, None)
        self.assertEqual(endpoint.server_url,
                         'http://openid.launchpad.dev/+openid')
        self.assertEqual(endpoint.local_id, None)


class MaybeFixupIdentifierSelectRequestTests(unittest.TestCase):
    """Tests for the maybe_fixup_identifier_select() helper."""

    def test_openid1(self):
        """Test that OpenID 1.1 requests are fixed up correctly.

        In this case, the claimed ID and local ID get changed to the
        expected claimed ID.  This is needed in order for the response
        not to look forged.
        """
        store = MemoryStore()
        consumer = Consumer(session={}, store=store)
        consumer.beginWithoutDiscovery(
            make_identifier_select_endpoint(OPENID_1_1_TYPE))
        endpoint = consumer.session[consumer._token_key]
        self.assertEqual(endpoint.claimed_id, IDENTIFIER_SELECT)
        self.assertEqual(endpoint.local_id, IDENTIFIER_SELECT)

        # The claimed ID and local ID are rewritten for OpenID 1.x
        # requests.
        maybe_fixup_identifier_select_request(
            consumer, 'http://example.com/identifier')
        self.assertEqual(endpoint.claimed_id, 'http://example.com/identifier')
        self.assertEqual(endpoint.local_id, 'http://example.com/identifier')

    def test_openid20(self):
        """Test that OpenID 2.0 requests are left untouched.

        The OpenID 2.0 standard supports identifier select, so no
        special handling is necessary.
        """
        store = MemoryStore()
        consumer = Consumer(session={}, store=store)
        consumer.beginWithoutDiscovery(
            make_identifier_select_endpoint(OPENID_2_0_TYPE))
        endpoint = consumer.session[consumer._token_key]
        self.assertEqual(endpoint.claimed_id, None)
        self.assertEqual(endpoint.local_id, None)

        # No change is made for OpenID 2.0 requests
        maybe_fixup_identifier_select_request(
            consumer, 'http://example.com/identifier')
        self.assertEqual(endpoint.claimed_id, None)
        self.assertEqual(endpoint.local_id, None)


class CompleteFromBrowserTests(unittest.TestCase):
    """Tests for the complete_from_browser() helper."""

    def test_complete_from_browser(self):
        """Test complete_from_browser()'s response parsing."""
        store = MemoryStore()
        consumer = Consumer(session={}, store=store)
        consumer.beginWithoutDiscovery(make_endpoint(
                OPENID_1_1_TYPE, 'http://example.com/identifier'))
        class FakeBrowser:
            contents = ('Consumer received GET\n'
                        'openid.mode:error\n'
                        'openid.error:foo:error\n')
        info = complete_from_browser(consumer, FakeBrowser)
        self.assertEqual(info.status, 'failure')
        self.assertEqual(info.message, 'foo:error')


def test_suite():
    suite = unittest.TestLoader().loadTestsFromName(__name__)

    # Add per-version page tests to the suite, once for each OpenID
    # version.
    pagetestsdir = os.path.join('..', 'pagetests', 'openid', 'per-version')
    for PROTOCOL_URI in [OPENID_1_1_TYPE, OPENID_2_0_TYPE]:
        def setUp(test, PROTOCOL_URI=PROTOCOL_URI):
            setUpGlobs(test)
            test.globs['PROTOCOL_URI'] = PROTOCOL_URI
        suite.addTest(PageTestSuite(pagetestsdir, setUp=setUp))
    return suite
