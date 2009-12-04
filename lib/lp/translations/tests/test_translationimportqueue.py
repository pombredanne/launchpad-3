# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0102

__metaclass__ = type

import unittest

from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue, RosettaImportStatus)
from lp.translations.utilities.translation_export import (
    LaunchpadWriteTarFile)

from lp.testing import TestCaseWithFactory
from canonical.testing import LaunchpadZopelessLayer


class TestTranslationImportQueueEntryStatus(TestCaseWithFactory):
    """Test handling of the status of a queue entry."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        super(TestTranslationImportQueueEntryStatus, self).setUp()

        self.queue = getUtility(ITranslationImportQueue)
        self.rosetta_experts = (
            getUtility(ILaunchpadCelebrities).rosetta_experts)
        self.productseries = self.factory.makeProductSeries()
        self.uploaderperson = self.factory.makePerson()
        self.potemplate = self.factory.makePOTemplate(
            productseries=self.productseries)
        self.entry = self.queue.addOrUpdateEntry(
            'demo.pot', '#demo', False, self.uploaderperson,
            productseries=self.productseries, potemplate=self.potemplate)

    def _assertCanSetStatus(self, user, entry, expected_list):
        # Helper to check for all statuses.
        # Could iterate RosettaImportStatus.items but listing them here
        # explicitely is better to read. They are sorted alphabetically.
        possible_statuses = [
            RosettaImportStatus.APPROVED,
            RosettaImportStatus.BLOCKED,
            RosettaImportStatus.DELETED,
            RosettaImportStatus.FAILED,
            RosettaImportStatus.IMPORTED,
            RosettaImportStatus.NEEDS_REVIEW,
        ]
        # Do *not* use assertContentEqual here, as the order matters.
        self.assertEqual(expected_list,
            [entry.canSetStatus(status, user)
                 for status in possible_statuses])

    def test_canSetStatus_non_admin(self):
        # A non-privileged users cannot set any status.
        some_user = self.factory.makePerson()
        self._assertCanSetStatus(some_user, self.entry,
            #  A      B      D      F      I     NR
            [False, False, False, False, False, False])

    def test_canSetStatus_rosetta_expert(self):
        # Rosetta experts are all-powerful, didn't you know that?
        self._assertCanSetStatus(self.rosetta_experts, self.entry,
            #  A     B     D     F     I    NR
            [True, True, True, True, True, True])

    def test_canSetStatus_rosetta_expert_no_target(self):
        # If the entry has no import target set, even Rosetta experts
        # cannot set it to approved.
        self.entry.potemplate = None
        self._assertCanSetStatus(self.rosetta_experts, self.entry,
            #  A      B     D     F     I    NR
            [False, True, True, True, True, True])

    def test_canSetStatus_uploader(self):
        # The uploader can set some statuses.
        self._assertCanSetStatus(self.uploaderperson, self.entry,
            #  A      B     D     F      I     NR
            [False, False, True, False, False, True])

    def test_canSetStatus_owner(self):
        # The owner gets the same permissions.
        self._assertCanSetStatus(self.productseries.product.owner, self.entry,
            #  A      B     D     F      I     NR
            [False, False, True, False, False, True])

    def _setUpUbuntu(self):
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.ubuntu_group_owner = self.factory.makePerson()
        self.ubuntu.translationgroup = (
            self.factory.makeTranslationGroup(self.ubuntu_group_owner))

    def test_canSetStatus_ubuntu_translation_group(self):
        # Owners of the Ubuntu translation Groups can set entries to approved
        # that are targeted to Ubuntu.
        self._setUpUbuntu()
        ubuntu_entry = self.queue.addOrUpdateEntry(
            'demo.pot', '#demo', False, self.uploaderperson,
            distroseries=self.factory.makeDistroRelease(self.ubuntu),
            sourcepackagename=self.factory.makeSourcePackageName(),
            potemplate=self.potemplate)
        self._assertCanSetStatus(self.ubuntu_group_owner, ubuntu_entry,
            #  A     B     D     F      I     NR
            [True, True, True, False, False, True])

    def test_canSetStatus_ubuntu_translation_group_not_ubuntu(self):
        # Outside of Ubuntu, owners of the Ubuntu translation Groups have no
        # powers.
        self._setUpUbuntu()
        self._assertCanSetStatus(self.ubuntu_group_owner, self.entry,
            #  A      B      D      F      I     NR
            [False, False, False, False, False, False])


class TestTranslationUpload(TestCaseWithFactory):
    """Test uploading of translations to the queue."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up context to test in."""
        super(TestTranslationImportQueueEntryStatus, self).setUp()

        self.queue = getUtility(ITranslationImportQueue)
        self.rosetta_experts = (
            getUtility(ILaunchpadCelebrities).rosetta_experts)

    def _make_tarball(self):
        tarball_content = {
            'foo.pot': 'Foo template',
            'es.po': 'Spanish translation',
            'fr.po': 'French translation',
            }
        return LaunchpadWriteTarFile.files_to_string(tarball_content)

    def test_addOrUpdateEntriesFromTarball_queued_user(self):
        # The method addOrUpdateEntriesFromTarball is called by the
        # archive uploader when uploading sourcepackages that provide
        # translations. The uploader uses a different db user (queued) and
        # the method must work within the permissions of that user.
        self.layer.switchDbUser('queued')
        distroseries = self.factory.makeDistroRelease()
        sourcepackagename = self.factory.makeSourcePackageName()
        sourcepackage = self.factory.makeSourcePackage(sourcepackagename,
                                                       distroseries)
        self.queue.addOrUpdateEntriesFromTarball(
            self._make_tarball(), True, self.rosetta_experts,
            sourcepackagename=sourcepackagename,
            distroseries=distroseries)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
