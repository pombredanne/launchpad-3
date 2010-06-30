# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive software center agent celebrity."""

from zope.component import getUtility
from canonical.launchpad.webapp.authorization import check_permission
from lp.soyuz.interfaces.archivesubscriber import IArchiveSubscriberSet
from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import login, login_person, TestCaseWithFactory


class TestArchivePrivacy(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.ppa = self.factory.makeArchive()
        login('admin@canonical.com')
        self.ppa.buildd_secret = 'blah'
        self.ppa.private = True
        self.ppa.commercial = True
        self.agent = self.factory.makePerson(name='software-center-agent')
        self.joe = self.factory.makePerson(name='joe')

    def test_check_permission(self):
        """The software center agent has the relevant permissions for a
        commercial archive, but not a private one.
        """
        login_person(self.agent)
        self.assertEqual(
            check_permission('launchpad.View', self.ppa), True)
        self.assertEqual(
            check_permission('launchpad.Append', self.ppa), True)

    def test_check_permission_private(self):
        ppa = self.factory.makeArchive()
        login('admin@canonical.com')
        ppa.buildd_secret = 'blah'
        ppa.private = True
        login_person(self.agent)
        self.assertEqual(check_permission('launchpad.View', ppa), False)
        self.assertEqual(check_permission('launchpad.Append', ppa), False)

    def test_add_subscription(self):
        login_person(self.agent)
        self.ppa.newSubscription(self.joe, self.agent)
        subscription = getUtility(
            IArchiveSubscriberSet).getBySubscriber(
            self.joe, archive=self.ppa).one()
        self.assertEqual(subscription.registrant, self.agent)
        self.assertEqual(subscription.subscriber, self.joe)

    def test_getPrivateSourcesList(self):
        login_person(self.agent)
        sources = self.ppa.getPrivateSourcesList(self.joe)
        authtoken = self.ppa.getAuthToken(self.joe).token
        url = self.ppa.archive_url.split('http://')[1]
        new_url = "http://joe:%s@%s" % (authtoken, url)
        self.assertEqual(sources, new_url)

