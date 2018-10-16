# Copyright 2011-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the webservice marshallers."""

__metaclass__ = type

from testtools.matchers import (
    Equals,
    MatchesDict,
    MatchesStructure,
    )
import transaction
from zope.component import adapter
from zope.interface import (
    implementer,
    Interface,
    )
from zope.schema import Choice

from lp.app.webservice.marshallers import (
    InlineObjectFieldMarshaller,
    TextFieldMarshaller,
    )
from lp.services.fields import (
    InlineObject,
    PersonChoice,
    )
from lp.services.job.interfaces.job import JobStatus
from lp.services.webapp.publisher import canonical_url
from lp.services.webapp.servers import WebServiceTestRequest
from lp.testing import (
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.fixture import ZopeAdapterFixture
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    LaunchpadWebServiceCaller,
    webservice_for_person,
    )


def ws_url(bug):
    url = "/bugs/%d" % bug.id
    return url


class TestTextFieldMarshaller(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_unmarshall_obfuscated(self):
        # Data is obfuscated if the user is anonynous.
        marshaller = TextFieldMarshaller(None, WebServiceTestRequest())
        result = marshaller.unmarshall(None, u"foo@example.com")
        self.assertEqual(u"<email address hidden>", result)

    def test_unmarshall_not_obfuscated(self):
        # Data is not obfuscated if the user is authenticated.
        marshaller = TextFieldMarshaller(None, WebServiceTestRequest())
        with person_logged_in(self.factory.makePerson()):
            result = marshaller.unmarshall(None, u"foo@example.com")
        self.assertEqual(u"foo@example.com", result)


class TestWebServiceObfuscation(TestCaseWithFactory):
    """Integration test for obfuscation marshaller.

    Not using WebServiceTestCase because that assumes too much about users
    """

    layer = DatabaseFunctionalLayer

    email_address = "joe@example.com"
    email_address_obfuscated = "<email address hidden>"
    email_address_obfuscated_escaped = "&lt;email address hidden&gt;"
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
        # Email addresses are obfuscated for anonymous users.
        bug = self._makeBug()
        logout()
        webservice = LaunchpadWebServiceCaller()
        result = webservice(ws_url(bug)).jsonBody()
        self.assertEqual(
            self.bug_title % self.email_address_obfuscated,
            result['title'])
        self.assertEqual(
            self.bug_description % self.email_address_obfuscated,
            result['description'])

    def test_email_address_not_obfuscated(self):
        # Email addresses are not obfuscated for authenticated users.
        bug = self._makeBug()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        result = webservice(ws_url(bug)).jsonBody()
        self.assertEqual(self.bug_title % self.email_address, result['title'])
        self.assertEqual(
            self.bug_description % self.email_address, result['description'])

    def test_xhtml_email_address_not_obfuscated(self):
        # Email addresses are not obfuscated for authenticated users.
        bug = self._makeBug()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        result = webservice(
            ws_url(bug), headers={'Accept': 'application/xhtml+xml'})
        self.assertIn(self.email_address, result.body)
        self.assertNotIn(
            self.email_address_obfuscated_escaped, result.body)

    def test_xhtml_email_address_obfuscated(self):
        # Email addresses are obfuscated in the XML representation for
        # anonymous users.
        bug = self._makeBug()
        logout()
        webservice = LaunchpadWebServiceCaller()
        result = webservice(
            ws_url(bug), headers={'Accept': 'application/xhtml+xml'})
        self.assertNotIn(self.email_address, result.body)
        self.assertIn(self.email_address_obfuscated_escaped, result.body)

    def test_etags_differ_for_anon_and_non_anon_represetations(self):
        # When a webservice client retrieves data anonymously, this
        # data should not be used in later write requests, if the
        # text fields contain obfuscated email addresses. The etag
        # for a GET request is calculated after the email address
        # obfuscation and thus differs from the etag returned for
        # not obfuscated data, so clients usings etags to check if the
        # cached data is up to date will not use the obfuscated data
        # in PATCH or PUT requests.
        bug = self._makeBug()
        user = self.factory.makePerson()
        webservice = webservice_for_person(user)
        etag_logged_in = webservice(ws_url(bug)).getheader('etag')
        logout()
        webservice = LaunchpadWebServiceCaller()
        etag_logged_out = webservice(ws_url(bug)).getheader('etag')
        self.assertNotEqual(etag_logged_in, etag_logged_out)


class IInlineExample(Interface):

    person = PersonChoice(vocabulary="ValidPersonOrTeam")

    status = Choice(vocabulary=JobStatus)


@implementer(IInlineExample)
class InlineExample:

    def __init__(self, person, status):
        self.person = person
        self.status = status


@adapter(dict)
@implementer(IInlineExample)
def inline_example_from_dict(template):
    return InlineExample(**template)


class TestInlineObjectFieldMarshaller(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_unmarshall(self):
        field = InlineObject(schema=IInlineExample)
        request = WebServiceTestRequest()
        request.setVirtualHostRoot(names=["devel"])
        marshaller = InlineObjectFieldMarshaller(field, request)
        obj = InlineExample(self.factory.makePerson(), JobStatus.WAITING)
        result = marshaller.unmarshall(None, obj)
        self.assertThat(result, MatchesDict({
            "person_link": Equals(canonical_url(obj.person, request=request)),
            "status": Equals("Waiting"),
            }))

    def test_marshall_from_json_data(self):
        self.useFixture(ZopeAdapterFixture(inline_example_from_dict))
        field = InlineObject(schema=IInlineExample)
        request = WebServiceTestRequest()
        request.setVirtualHostRoot(names=["devel"])
        marshaller = InlineObjectFieldMarshaller(field, request)
        person = self.factory.makePerson()
        data = {
            "person_link": canonical_url(person, request=request),
            "status": "Running",
            }
        obj = marshaller.marshall_from_json_data(data)
        self.assertThat(obj, MatchesStructure.byEquality(
            person=person, status=JobStatus.RUNNING))
