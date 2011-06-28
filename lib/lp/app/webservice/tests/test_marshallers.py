# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the webservice marshallers."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import IPlacelessAuthUtility
from canonical.launchpad.webapp.servers import WebServiceTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.webservice.marshallers import TextFieldMarshaller
from lp.testing import TestCaseWithFactory



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
