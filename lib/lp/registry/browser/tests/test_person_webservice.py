# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    launchpadlib_for,
    TestCaseWithFactory,
    )


class TestPersonEmailSecurity(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonEmailSecurity, self).setUp()
        self.target = self.factory.makePerson(name='target')
        self.email_one = self.factory.makeEmail(
                'test1@example.com', self.target)
        self.email_two = self.factory.makeEmail(
                'test2@example.com', self.target)

    def test_logged_in_can_access(self):
        # A logged in launchpadlib connection can see confirmed email
        # addresses.
        accessor = self.factory.makePerson()
        lp = launchpadlib_for("test", accessor.name)
        person = lp.people['target']
        emails = sorted(list(person.confirmed_email_addresses))
        self.assertNotEqual(
                sorted([self.email_one, self.email_two]),
                len(emails))

    def test_anonymous_cannot_access(self):
        # An anonymous launchpadlib connection cannot see email addresses.

        # Need to endInteraction() because launchpadlib_for() will
        # setup a new one.
        endInteraction()
        lp = launchpadlib_for('test', person=None, version='devel')
        person = lp.people['target']
        emails = list(person.confirmed_email_addresses)
        self.assertEqual([], emails)


class TestPersonRepresentation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('guilherme.salgado@canonical.com ')
        self.person = self.factory.makePerson(
            name='test-person', displayname='Test Person')
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_GET_xhtml_representation(self):
        # Remove the security proxy because IPerson.name is protected.
        person_name = removeSecurityProxy(self.person).name
        response = self.webservice.get(
            '/~%s' % person_name, 'application/xhtml+xml')

        self.assertEqual(response.status, 200)

        rendered_comment = response.body
        self.assertEquals(
            rendered_comment,
            '<a href="/~test-person" class="sprite person">Test Person</a>')
