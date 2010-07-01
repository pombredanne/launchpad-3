# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing registry-related xmlrpc calls."""

__metaclass__ = type

import unittest
import xmlrpclib
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.functional import XMLRPCTestTransport
from canonical.launchpad.interfaces import IPrivateApplication
from canonical.launchpad.interfaces.account import AccountStatus
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.interfaces.person import (
    IPersonSet, IPersonSetAPIView, IPersonSetApplication,
    PersonCreationRationale)
from lp.registry.xmlrpc.personset import PersonSetAPIView
from lp.testing import TestCaseWithFactory


class TestPersonSetAPIInterfaces(TestCaseWithFactory):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestPersonSetAPIInterfaces, self).setUp()
        self.private_root = getUtility(IPrivateApplication)
        self.personset_api = PersonSetAPIView(
            context=self.private_root.personset,
            request=LaunchpadTestRequest())

    def test_provides_interface(self):
        # The application and api interfaces are provided.
        self.assertProvides(self.private_root.personset, IPersonSetApplication)
        self.assertProvides(self.personset_api, IPersonSetAPIView)

    def test_getOrCreateByOpenIDIdentifier(self):
        # The method returns the username of the person, and sets the
        # correct creation rational/comment.
        user_name = self.personset_api.getOrCreateByOpenIDIdentifier(
            'openid-ident', 'a@b.com', 'Joe Blogs')

        person = getUtility(IPersonSet).getByName(user_name)
        self.assertEqual(
            'openid-ident', removeSecurityProxy(person.account).openid_identifier)
        self.assertEqual(
            PersonCreationRationale.SOFTWARE_CENTER_PURCHASE,
            person.creation_rationale)
        self.assertEqual(
            "when purchasing an application via Software Center.",
            person.creation_comment)

    def test_getOrCreateByOpenIDIdentifier_xmlrpc(self):
        # The method can be called via xmlrpc
        personset_api_rpc = xmlrpclib.ServerProxy(
            'http://xmlrpc-private.launchpad.dev:8087/personset',
            transport=XMLRPCTestTransport())

        user_name = personset_api_rpc.getOrCreateByOpenIDIdentifier(
            'openid-ident', 'a@b.com', 'Joe Blogs')
        person = getUtility(IPersonSet).getByName(user_name)
        self.assertEqual(
            'openid-ident', removeSecurityProxy(person.account).openid_identifier)

    def test_getOrCreateByOpenIDIdentifier_xmlrpc_error(self):
        suspended_account = self.factory.makeAccount(
            'Joe Blogs', email='a@b.com', status=AccountStatus.SUSPENDED)
        openid_identifier = removeSecurityProxy(
            suspended_account).openid_identifier
        personset_api_rpc = xmlrpclib.ServerProxy(
            'http://xmlrpc-private.launchpad.dev:8087/personset',
            transport=XMLRPCTestTransport())

        # assertRaises doesn't let us check the type of Fault.
        fault_raised = False
        try:
            user_name = personset_api_rpc.getOrCreateByOpenIDIdentifier(
                openid_identifier, 'a@b.com', 'Joe Blogs')
        except xmlrpclib.Fault, e:
            fault_raised = True
            self.assertEqual(370, e.faultCode)
            self.assertIn(openid_identifier, e.faultString)

        self.assertTrue(fault_raised)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
