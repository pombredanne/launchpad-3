# Copyright 2010-2012 Canonical Ltd.  This software is licensed under the GNU
# Affero General Public License version 3 (see the file LICENSE).

"""Test Archive software center agent celebrity."""

from zope.component import getUtility

from lp.services.webapp.authorization import check_permission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriberSet
from lp.testing import (
    celebrity_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestArchivePrivacy(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_check_permission(self):
        """The software center agent has the relevant permissions for a
        commercial archive, but not a private one.
        """
        ppa = self.factory.makeArchive(private=True, commercial=True)
        with celebrity_logged_in('software_center_agent'):
            self.assertEqual(check_permission('launchpad.View', ppa), True)
            self.assertEqual(check_permission('launchpad.Append', ppa), True)

    def test_check_permission_private(self):
        ppa = self.factory.makeArchive(private=True, commercial=False)
        with celebrity_logged_in('software_center_agent'):
            self.assertEqual(check_permission('launchpad.View', ppa), False)
            self.assertEqual(check_permission('launchpad.Append', ppa), False)

    def test_add_subscription(self):
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(private=True, commercial=True)
        with celebrity_logged_in('software_center_agent') as agent:
            ppa.newSubscription(person, agent)
            subscription = getUtility(IArchiveSubscriberSet).getBySubscriber(
                person, archive=ppa).one()
            self.assertEqual(subscription.registrant, agent)
            self.assertEqual(subscription.subscriber, person)

    def test_getArchiveSubscriptionURL(self):
        ppa = self.factory.makeArchive(private=True, commercial=True)
        person = self.factory.makePerson()
        with celebrity_logged_in('software_center_agent') as agent:
            sources = person.getArchiveSubscriptionURL(agent, ppa)
            authtoken = ppa.getAuthToken(person).token
            url = ppa.archive_url.split('http://')[1]
        new_url = "http://%s:%s@%s" % (person.name, authtoken, url)
        self.assertEqual(sources, new_url)
