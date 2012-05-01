# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive privacy features."""

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from lp.soyuz.interfaces.archive import (
    CannotSwitchPrivacy,
    IArchiveSet,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadZopelessLayer,
    )


class TestArchivePrivacy(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.private_ppa = self.factory.makeArchive(
            description='Foo', private=True)
        self.joe = self.factory.makePerson(name='joe')
        self.fred = self.factory.makePerson(name='fred')
        login_person(self.private_ppa.owner)
        self.private_ppa.newSubscription(self.joe, self.private_ppa.owner)

    def test_no_subscription(self):
        login_person(self.fred)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertRaises(Unauthorized, getattr, p3a, 'description')

    def test_subscription(self):
        login_person(self.joe)
        p3a = getUtility(IArchiveSet).get(self.private_ppa.id)
        self.assertEqual(p3a.description, "Foo")


class TestArchivePrivacySwitching(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def set_ppa_privacy(self, ppa, private):
        """Helper method to privatise a ppa."""
        ppa.private = private

    def test_switch_privacy_no_pubs_succeeds(self):
        # Changing the privacy is fine if there are no publishing
        # records.
        public_ppa = self.factory.makeArchive()
        self.set_ppa_privacy(public_ppa, private=True)
        self.assertTrue(public_ppa.private)

        private_ppa = self.factory.makeArchive(private=True)
        self.set_ppa_privacy(private_ppa, private=False)
        self.assertFalse(private_ppa.private)

    def test_switch_privacy_with_pubs_fails(self):
        # Changing the privacy is not possible when the archive already
        # has published sources.
        public_ppa = self.factory.makeArchive(private=False)
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()

        private_ppa = self.factory.makeArchive(private=True)
        publisher.getPubSource(archive=public_ppa)
        publisher.getPubSource(archive=private_ppa)

        self.assertRaises(
            CannotSwitchPrivacy,
            self.set_ppa_privacy, public_ppa, private=True)

        self.assertRaises(
            CannotSwitchPrivacy,
            self.set_ppa_privacy, private_ppa, private=False)

    def test_buildd_secret_was_generated(self):
        public_ppa = self.factory.makeArchive()
        self.set_ppa_privacy(public_ppa, private=True)
        self.assertNotEqual(public_ppa.buildd_secret, None)

    def test_discard_buildd_was_discarded(self):
        private_ppa = self.factory.makeArchive(private=True)
        self.set_ppa_privacy(private_ppa, private=False)
        self.assertEqual(private_ppa.buildd_secret, None)
