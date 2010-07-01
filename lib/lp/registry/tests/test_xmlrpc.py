# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing registry-related xmlrpc calls."""

__metaclass__ = type

import unittest
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces import IPrivateApplication
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import (
    IPersonSetAPIView, IPersonSetApplication, PersonCreationRationale)
from lp.registry.xmlrpc.personset import PersonSetAPIView
from lp.testing import login_person, TestCaseWithFactory


class TestPersonSetAPIInterfaces(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPersonSetAPIInterfaces, self).setUp()
        self.private_root = getUtility(IPrivateApplication)
        self.personset_api = PersonSetAPIView(
            context=self.private_root.personset,
            request=LaunchpadTestRequest())

    def test_provides_interface(self):
        self.assertProvides(self.private_root.personset, IPersonSetApplication)
        self.assertProvides(self.personset_api, IPersonSetAPIView)

    def test_getOrCreateByOpenIDIdentifier(self):
        person = self.personset_api.getOrCreateByOpenIDIdentifier(
            'openid-ident', 'a@b.com', 'Joe Blogs')

        self.assertEqual(
            'openid-ident', removeSecurityProxy(person.account).openid_identifier)
        self.assertEqual(
            PersonCreationRationale.SOFTWARE_CENTER_PURCHASE,
            person.creation_rationale)
        self.assertEqual(
            "when purchasing an application via Software Center.",
            person.creation_comment)


    def test_requires_admin_or_agent(self):
        person = self.factory.makePerson()
        login_person(person)
        import xmlrpclib
        from canonical.functional import XMLRPCTestTransport
        personset_api_rpc = xmlrpclib.ServerProxy(
            'http://xmlrpc-private.launchpad.dev:8087/personset',
            transport=XMLRPCTestTransport())

        person = personset_api_rpc.getOrCreateByOpenIDIdentifier(
            'openid-ident', 'a@b.com', 'Joe Blogs')
        import pdb;pdb.set_trace()



def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
