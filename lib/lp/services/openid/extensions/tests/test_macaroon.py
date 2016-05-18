# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from openid.consumer.consumer import SuccessResponse
from openid.message import IDENTIFIER_SELECT
from openid.server.server import Server
from zope.component import getUtility

from lp.services.openid.extensions.macaroon import (
    MACAROON_NS,
    MacaroonNamespaceError,
    MacaroonRequest,
    MacaroonResponse,
    get_macaroon_ns,
    )
from lp.services.openid.interfaces.openidconsumer import IOpenIDConsumerStore
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.layers import ZopelessDatabaseLayer
from lp.testopenid.interfaces.server import get_server_url


class TestGetMacaroonNS(TestCase):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestGetMacaroonNS, self).setUp()
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        self.orequest = openid_server.decodeRequest(params)

    def test_get_macaroon_ns(self):
        message = self.orequest.message
        self.assertIsNone(message.namespaces.getAlias(MACAROON_NS))
        uri = get_macaroon_ns(message)
        self.assertEqual(MACAROON_NS, uri)
        self.assertEqual('macaroon', message.namespaces.getAlias(MACAROON_NS))

    def test_get_macaroon_ns_alias_already_exists(self):
        message = self.orequest.message
        message.namespaces.addAlias('http://localhost/', 'macaroon')
        self.assertIsNone(message.namespaces.getAlias(MACAROON_NS))
        self.assertRaises(MacaroonNamespaceError, get_macaroon_ns, message)


class TestMacaroonRequest(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestMacaroonRequest, self).setUp()
        self.caveat_id = self.factory.getUniqueUnicode()
        self.req = MacaroonRequest(self.caveat_id)

    def test_init(self):
        req = MacaroonRequest()
        self.assertIsNone(req.caveat_id)
        self.assertEqual(MACAROON_NS, req.ns_uri)

        self.assertEqual(self.caveat_id, self.req.caveat_id)

    def test_fromOpenIDRequest(self):
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        orequest = openid_server.decodeRequest(params)
        req = MacaroonRequest.fromOpenIDRequest(orequest)
        self.assertIsNone(req.caveat_id)
        self.assertEqual(MACAROON_NS, req.ns_uri)

    def test_fromOpenIDRequest_with_root(self):
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            'openid.macaroon.caveat_id': self.caveat_id,
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        orequest = openid_server.decodeRequest(params)
        req = MacaroonRequest.fromOpenIDRequest(orequest)
        self.assertEqual(self.caveat_id, req.caveat_id)
        self.assertEqual(MACAROON_NS, req.ns_uri)

    def test_parseExtensionArgs(self):
        req = MacaroonRequest()
        req.parseExtensionArgs({'caveat_id': self.caveat_id})
        self.assertEqual(self.caveat_id, req.caveat_id)

    def test_getExtensionArgs(self):
        expected = {'caveat_id': self.caveat_id}
        self.assertEqual(expected, self.req.getExtensionArgs())

    def test_getExtensionArgs_no_root(self):
        req = MacaroonRequest()
        self.assertEqual({}, req.getExtensionArgs())


class TestMacaroonResponse(TestCase):

    layer = ZopelessDatabaseLayer

    def test_init(self):
        resp = MacaroonResponse()
        self.assertIsNone(resp.discharge_macaroon_raw)
        self.assertEqual(MACAROON_NS, resp.ns_uri)

        resp = MacaroonResponse(discharge_macaroon_raw='dummy')
        self.assertEqual('dummy', resp.discharge_macaroon_raw)

    def test_extractResponse(self):
        req = MacaroonRequest()
        resp = MacaroonResponse.extractResponse(req, 'dummy')
        self.assertEqual(req.ns_uri, resp.ns_uri, req.ns_uri)
        self.assertEqual('dummy', resp.discharge_macaroon_raw)

    def test_fromSuccessResponse_signed_present(self):
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            'openid.macaroon.discharge': 'dummy',
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        orequest = openid_server.decodeRequest(params)
        signed_fields = ['openid.macaroon.discharge']
        success_resp = SuccessResponse(
            orequest, orequest.message, signed_fields=signed_fields)
        resp = MacaroonResponse.fromSuccessResponse(success_resp)
        self.assertEqual('dummy', resp.discharge_macaroon_raw)

    def test_fromSuccessResponse_no_signed(self):
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        orequest = openid_server.decodeRequest(params)
        success_resp = SuccessResponse(orequest, orequest.message)
        resp = MacaroonResponse.fromSuccessResponse(success_resp)
        self.assertIsNone(resp.discharge_macaroon_raw)

    def test_fromSuccessResponse_all(self):
        params = {
            'openid.mode': 'checkid_setup',
            'openid.trust_root': 'http://localhost/',
            'openid.return_to': 'http://localhost/',
            'openid.identity': IDENTIFIER_SELECT,
            'openid.macaroon.discharge': 'dummy',
            }
        openid_store = getUtility(IOpenIDConsumerStore)
        openid_server = Server(openid_store, get_server_url())
        orequest = openid_server.decodeRequest(params)
        success_resp = SuccessResponse(orequest, orequest.message)
        resp = MacaroonResponse.fromSuccessResponse(success_resp, False)
        self.assertEqual('dummy', resp.discharge_macaroon_raw)

    def test_getExtensionArgs(self):
        expected = {'discharge': 'dummy'}
        req = MacaroonResponse(discharge_macaroon_raw='dummy')
        self.assertEqual(req.getExtensionArgs(), expected)
