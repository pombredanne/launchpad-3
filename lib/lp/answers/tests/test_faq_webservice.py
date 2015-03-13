# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lazr.lifecycle.event import ObjectModifiedEvent
from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    MatchesRegex,
    )
from zope.event import notify

from lp.testing import (
    admin_logged_in,
    api_url,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import webservice_for_person


class TestFAQWebService(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_representation(self):
        with admin_logged_in():
            faq = self.factory.makeFAQ(title="Nothing works")
            faq.keywords = "foo bar"
            faq.content = "It is all broken."
            notify(ObjectModifiedEvent(
                faq, faq, ['keywords', 'content'], user=faq.owner))
            faq_url = api_url(faq)
        webservice = webservice_for_person(self.factory.makePerson())
        repr = webservice.get(faq_url, api_version='devel').jsonBody()
        with admin_logged_in():
            self.assertThat(
                repr,
                ContainsDict({
                    "id": Equals(faq.id),
                    "title": Equals("Nothing works"),
                    "keywords": Equals("foo bar"),
                    "content": Equals("It is all broken."),
                    "date_created": MatchesRegex("\d\d\d\d-\d\d-\d\dT.*"),
                    "date_last_updated": MatchesRegex("\d\d\d\d-\d\d-\d\dT.*"),
                    "last_updated_by_link": Contains(
                        "/devel/~%s" % faq.owner.name),
                    "target_link": Contains(
                        "/devel/%s" % faq.target.name),
                    }))
