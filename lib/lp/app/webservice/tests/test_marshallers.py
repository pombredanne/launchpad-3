# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the webservice marshallers."""

__metaclass__ = type

import transaction
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.servers import WebServiceTestRequest
from canonical.testing.layers import (
    AppServerLayer,
    DatabaseFunctionalLayer,
    )
from lp.app.webservice.marshallers import TextFieldMarshaller
from lp.testing import (
    TestCaseWithFactory,
    ws_object,
    )


class TestTextFieldMarshaller(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def _makeRequest(self, is_anonymous):
        """Create either an anonymous or authenticated request."""
        request = WebServiceTestRequest()
        if is_anonymous:
            request.setPrincipal(
                getUtility(IPlacelessAuthUtility).unauthenticatedPrincipal())
        else:
            request.setPrincipal(self.factory.makePerson())
        return request

    def test_unmarshall_obfuscated(self):
        # Data is obfuccated if the request is anonynous.
        request = self._makeRequest(is_anonymous=True)
        marshaller = TextFieldMarshaller(None, request)
        result = marshaller.unmarshall(None, u"foo@example.com")
        self.assertEqual(u"<email address hidden>", result)

    def test_unmarshall_not_obfuscated(self):
        # Data is not obfuccated if the request is authenticated.
        request = self._makeRequest(is_anonymous=False)
        marshaller = TextFieldMarshaller(None, request)
        result = marshaller.unmarshall(None, u"foo@example.com")
        self.assertEqual(u"foo@example.com", result)

class TestWebServiceObfuscation(TestCaseWithFactory):
    """Integration test for obfuscation marshaller.

    Not using WebServiceTestCase because that assumes too much about users
    """

    layer = AppServerLayer

    email_address = "joe@example.com"
    email_address_obfuscated = "<email address hidden>"
    bug_title = "Title with address %s in it"
    bug_description = "Description with address %s in it"

    def _makeBug(self):
        """Create a bug with an email address in title and description."""
        bug = self.factory.makeBug(
            title=self.bug_title % self.email_address,
            description=self.bug_description % self.email_address)
        transaction.commit()
        return bug

    def test_email_address_obfuscated(self):
        # Email address are obfuscated for anonymous users.
        ws = self.factory.makeLaunchpadService(anonymous=True)
        bug = self._makeBug()
        ws_bug = ws_object(ws, bug)
        self.assertEqual(
            self.bug_title % self.email_address_obfuscated,
            ws_bug.title)
        self.assertEqual(
            self.bug_description % self.email_address_obfuscated,
            ws_bug.description)

    def test_email_address_not_obfuscated(self):
        # Email address are not obfuscated for authendticated users.
        ws = self.factory.makeLaunchpadService(anonymous=False)
        bug = self._makeBug()
        ws_bug = ws_object(ws, bug)
        self.assertEqual(
            self.bug_title % self.email_address, ws_bug.title)
        self.assertEqual(
            self.bug_description % self.email_address, ws_bug.description)
