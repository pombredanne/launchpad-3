# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import (
    Contains,
    ContainsDict,
    Equals,
    MatchesRegex,
    )
from zope.component import getUtility

from lp.registry.interfaces.person import IPersonSet
from lp.services.webapp.interfaces import OAuthPermission
from lp.services.webapp.snapshot import notify_modified
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
            with notify_modified(faq, ['keywords', 'content'], user=faq.owner):
                faq.keywords = "foo bar"
                faq.content = "It is all broken."
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

    def test_delete(self):
        with admin_logged_in():
            faq = self.factory.makeFAQ()
            faq_url = api_url(faq)
            expert = self.factory.makePerson(
                member_of=[getUtility(IPersonSet).getByName('registry')])
        webservice = webservice_for_person(
            expert, permission=OAuthPermission.WRITE_PRIVATE)
        response = webservice.delete(faq_url, api_version='devel')
        self.assertEqual(200, response.status)
        response = webservice.get(faq_url, api_version='devel')
        self.assertEqual(404, response.status)
