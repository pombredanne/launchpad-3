# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive privacy features."""

from zope.component import getUtility
from lp.soyuz.interfaces.archive import IArchiveSet

from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import login, login_person, TestCaseWithFactory


class TestArchivePrivacy(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        owner = self.factory.makePerson()
        self.private_ppa = self.factory.makeArchive(
            owner=owner, description='Foo')
        login('admin@canonical.com')
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True
        self.joe = self.factory.makePerson(name='joe')
        self.fred = self.factory.makePerson(name='fred')
        login_person(owner)
        self.private_ppa.newSubscription(self.joe, owner)

    def test_no_subscription(self):
        login_person(self.fred)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertRaises(p3a.description, Unauthorized)

    def test_subscription(self):
        login_person(self.joe)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertEqual(p3a.description, "Foo")

