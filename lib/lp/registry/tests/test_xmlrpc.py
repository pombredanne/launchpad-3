# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing registry-related xmlrpc calls."""

__metaclass__ = type

import xmlrpclib

from zope.security.proxy import removeSecurityProxy

from lp.registry.enums import PersonVisibility
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.xmlrpc import XMLRPCTestTransport


class TestCanonicalSSOApplication(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestCanonicalSSOApplication, self).setUp()
        self.rpc_proxy = xmlrpclib.ServerProxy(
            'http://xmlrpc-private.launchpad.dev:8087/canonicalsso',
            transport=XMLRPCTestTransport())

    def test_getPersonDetailsByOpenIDIdentifier(self):
        person = self.factory.makePerson(time_zone='Australia/Melbourne')
        self.factory.makeTeam(
            name='pubteam', members=[person],
            visibility=PersonVisibility.PUBLIC)
        self.factory.makeTeam(
            name='privteam', members=[person],
            visibility=PersonVisibility.PRIVATE)
        openid_identifier = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier
        result = self.rpc_proxy.getPersonDetailsByOpenIDIdentifier(
            openid_identifier)
        self.assertEqual(
            dict(
                name=person.name,
                time_zone=person.location.time_zone,
                teams={'pubteam': False, 'privteam': True}),
            result)

    def test_not_available_on_public_api(self):
        # The person set api is not available on the public xmlrpc
        # service.
        person = self.factory.makePerson()
        openid_identifier = removeSecurityProxy(
            person.account).openid_identifiers.any().identifier
        public_rpc_proxy = xmlrpclib.ServerProxy(
            'http://test@canonical.com:test@'
            'xmlrpc.launchpad.dev/canonicalsso',
            transport=XMLRPCTestTransport())
        e = self.assertRaises(
            xmlrpclib.ProtocolError,
            public_rpc_proxy.getPersonDetailsByOpenIDIdentifier,
            openid_identifier)
        self.assertEqual(404, e.errcode)
