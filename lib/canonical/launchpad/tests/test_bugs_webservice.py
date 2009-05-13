# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

import unittest

from BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from simplejson import dumps

from canonical.launchpad.ftests import login
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing import DatabaseFunctionalLayer


class TestBugDescriptionRepresentation(unittest.TestCase):
    """Test ways of interacting with Bug webservice representations."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        login('foo.bar@canonical.com')
        self.factory = LaunchpadObjectFactory()
        # Make two bugs, one whose description points to the other, so it will
        # get turned into a HTML link.
        self.bug_one = self.factory.makeBug(title="generic")
        self.bug_two = self.factory.makeBug(
            description="Useless bugs are useless. See Bug %d." % (
            self.bug_one.id))

        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def findBugDescription(self, response):
        """Find the bug description field in an XHTML document fragment."""
        soup = BeautifulStoneSoup(response.consumeBody())
        dt = soup.find('dt', text="description").parent
        dd = dt.findNextSibling('dd')
        return str(dd.contents.pop())

    def test_GET_xhtml_representation(self):
        response = self.webservice.get(
            '/bugs/' + str(self.bug_two.id),
            'application/xhtml+xml')

        self.assertEqual(response.getStatus(), 200)

        self.assertEqual(
            self.findBugDescription(response),
            u'<p>Useless bugs are useless. '
            'See <a href="/bugs/%d" title="generic">Bug %d</a>.</p>' % (
            self.bug_one.id, self.bug_one.id))

    def test_PATCH_xhtml_representation(self):
        new_description = "See bug %d" % self.bug_one.id

        bug_two_json = self.webservice.get(
            '/bugs/%d' % self.bug_two.id).jsonBody()

        response = self.webservice.patch(
            bug_two_json['self_link'],
            'application/json',
            dumps(dict(description=new_description)),
            headers=dict(accept='application/xhtml+xml'))

        self.assertEqual(response.getStatus(), 209)

        self.assertEqual(
            self.findBugDescription(response),
            u'<p>See <a href="/bugs/%d" title="generic">bug %d</a></p>' % (
            self.bug_one.id, self.bug_one.id))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

