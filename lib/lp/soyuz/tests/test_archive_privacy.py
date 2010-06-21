# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive privacy features."""

from zope.component import getUtility
from lp.soyuz.interfaces.archive import IArchiveSet

from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory


class TestArchivePrivacy(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.owner = self.factory.makePerson()
        self.private_ppa = self.factory.makeArchive(owner=self.owner)
        self.private_ppa.buildd_secret = 'blah'
        self.private_ppa.private = True
        self.joe = self.factory.makePerson(name='joe')

    def test_no_subscription(self):
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertEqual(p3a, None)

    def test_subscription(self):
        self.private_ppa.newSubscription(self.joe, self.owner)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertEqual(p3a.id, self.private_ppa.id)

