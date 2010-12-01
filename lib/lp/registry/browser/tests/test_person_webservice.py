# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from zope.security.management import endInteraction
from zope.security.proxy import removeSecurityProxy

from launchpadlib.launchpad import Launchpad

from canonical.launchpad.ftests import login
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    launchpadlib_for,
    launchpadlib_for_anonymous,
    TestCaseWithFactory,
    )


class TestPersonEmailSecurity(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer
   
    def test_logged_in_can_access(self):
        # A logged in launchpadlib connection can see confirmed email
        # addresses. 
        lp = launchpadlib_for("test", "mark")
        person = lp.people['name12']
        emails = list(person.confirmed_email_addresses)
        self.assertNotEqual(0, len(emails))

    def test_anonymous_cannot_access(self):
        # An anonymous launchpadlib connection cannot see email addresses.

        # Need to endInteraction() because launchpadlib_for_anonymous() will
        # setup a new one.
        endInteraction()
        lp = launchpadlib_for_anonymous('test', version='devel')
        person = lp.people['name12']
        emails = list(person.confirmed_email_addresses)
        self.assertEqual(0, len(emails))


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
