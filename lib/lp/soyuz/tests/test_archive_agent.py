# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Test Archive software center agent celebrity."""

from __future__ import absolute_import, print_function, unicode_literals

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.testing import (
    celebrity_logged_in,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestSoftwareCenterAgent(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_getArchiveSubscriptionURL(self):
        # The software center agent can get subscription URLs for any
        # subscriber of the archive.
        owner = self.factory.makePerson()
        agent = getUtility(ILaunchpadCelebrities).software_center_agent
        ppa_owner = self.factory.makeTeam(members=[owner, agent])
        ppa = self.factory.makeArchive(owner=ppa_owner, private=True)
        person = self.factory.makePerson()
        # An error is raised if the user is not subscribed.
        with celebrity_logged_in('software_center_agent') as agent:
            self.assertRaises(
                Unauthorized,
                person.getArchiveSubscriptionURL, agent, ppa)
        # The PPA owner can create a valid subscription.
        with person_logged_in(ppa_owner):
            ppa.newSubscription(person, ppa_owner)
        # Now the agent can access a subscription URL.
        with celebrity_logged_in('software_center_agent') as agent:
            sources = person.getArchiveSubscriptionURL(agent, ppa)
        with person_logged_in(ppa.owner):
            authtoken = ppa.getAuthToken(person).token
            url = ppa.archive_url.split('http://')[1]
        new_url = "http://%s:%s@%s" % (person.name, authtoken, url)
        self.assertEqual(sources, new_url)
