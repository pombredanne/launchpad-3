# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive software center agent celebrity."""

from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.services.webapp.authorization import check_permission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriberSet
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestArchivePrivacy(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.agent = getUtility(ILaunchpadCelebrities).software_center_agent

    def test_check_permission(self):
        """The software center agent has the relevant permissions for a
        commercial archive, but not a private one.
        """
        ppa = self.factory.makeArchive(private=True, commercial=True)
        login_person(self.agent)
        self.assertEqual(check_permission('launchpad.View', ppa), True)
        self.assertEqual(check_permission('launchpad.Append', ppa), True)

    def test_check_permission_private(self):
        ppa = self.factory.makeArchive(private=True, commercial=False)
        login_person(self.agent)
        self.assertEqual(check_permission('launchpad.View', ppa), False)
        self.assertEqual(check_permission('launchpad.Append', ppa), False)

    def test_add_subscription(self):
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(private=True, commercial=True)
        login_person(self.agent)
        ppa.newSubscription(person, self.agent)
        subscription = getUtility(IArchiveSubscriberSet).getBySubscriber(
            person, archive=ppa).one()
        self.assertEqual(subscription.registrant, self.agent)
        self.assertEqual(subscription.subscriber, person)

    def test_getArchiveSubscriptionURL(self):
        ppa = self.factory.makeArchive(private=True, commercial=True)
        person = self.factory.makePerson()
        login_person(self.agent)
        sources = person.getArchiveSubscriptionURL(self.agent, ppa)
        authtoken = ppa.getAuthToken(person).token
        url = ppa.archive_url.split('http://')[1]
        new_url = "http://%s:%s@%s" % (person.name, authtoken, url)
        self.assertEqual(sources, new_url)
