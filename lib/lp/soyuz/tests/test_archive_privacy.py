# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive privacy features."""

from zope.component import getUtility
from zope.security.interfaces import Unauthorized
from lp.soyuz.interfaces.archive import IArchiveSet

from canonical.testing import LaunchpadFunctionalLayer
from lp.testing import login, login_person, TestCaseWithFactory


class TestArchivePrivacy(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.private_ppa = self.factory.makeArchive(description='Foo')
        login('admin@canonical.com')
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True
        self.joe = self.factory.makePerson(name='joe')
        self.fred = self.factory.makePerson(name='fred')
        login_person(self.private_ppa.owner)
        self.private_ppa.newSubscription(self.joe, self.private_ppa.owner)

    def _getDescription(self, p3a):
        return p3a.description

    def test_no_subscription(self):
        login_person(self.fred)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertRaises(Unauthorized, self._getDescription, p3a)

    def test_subscription(self):
        login_person(self.joe)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertEqual(self._getDescription(p3a), "Foo")

