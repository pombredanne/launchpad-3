# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Archive privacy features."""

from zope.component import getUtility
from zope.security.interfaces import Unauthorized

from canonical.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )
from lp.soyuz.interfaces.archive import (
    CannotSwitchPrivacy,
    IArchiveSet,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    login,
    login_person,
    TestCaseWithFactory,
    )


class TestArchivePrivacy(TestCaseWithFactory):
    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestArchivePrivacy, self).setUp()
        self.private_ppa = self.factory.makeArchive(description='Foo')
        login('admin@canonical.com')
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


class TestArchivePrivacySwitching(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Create a public and a private PPA."""
        super(TestArchivePrivacySwitching, self).setUp()
        self.public_ppa = self.factory.makeArchive()
        self.private_ppa = self.factory.makeArchive()
        self.private_ppa.private = True

    def make_ppa_private(self, ppa):
        """Helper method to privatise a ppa."""
        ppa.private = True

    def make_ppa_public(self, ppa):
        """Helper method to make a PPA public (and use for assertRaises)."""
        ppa.private = False

    def test_switch_privacy_no_pubs_succeeds(self):
        # Changing the privacy is fine if there are no publishing
        # records.
        self.make_ppa_private(self.public_ppa)
        self.assertTrue(self.public_ppa.private)

        self.private_ppa.private = False
        self.assertFalse(self.private_ppa.private)

    def test_switch_privacy_with_pubs_fails(self):
        # Changing the privacy is not possible when the archive already
        # has published sources.
        publisher = SoyuzTestPublisher()
        publisher.prepareBreezyAutotest()
        publisher.getPubSource(archive=self.public_ppa)
        publisher.getPubSource(archive=self.private_ppa)

        self.assertRaises(
            CannotSwitchPrivacy, self.make_ppa_private, self.public_ppa)

        self.assertRaises(
            CannotSwitchPrivacy, self.make_ppa_public, self.private_ppa)

    def test_buildd_secret_was_generated(self):
        self.make_ppa_private(self.public_ppa)
        self.assertNotEqual(self.public_ppa.buildd_secret, None)

    def test_discard_buildd_was_discarded(self):
        self.make_ppa_public(self.private_ppa)
        self.assertEqual(self.private_ppa.buildd_secret, None)
