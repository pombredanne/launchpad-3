# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the permissions for uploading to an archive."""

__metaclass__ = type

import unittest

from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer

from lp.archiveuploader.permission import CannotUploadToArchive, verify_upload
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.testing import TestCaseWithFactory


class TestPermission(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertCanUpload(self, person, ssp, archive):
        """Assert that 'person' can upload 'ssp' to 'archive'."""
        # For now, just check that doesn't raise an exception.
        verify_upload(person, ssp, archive)

    def test_random_person_cannot_upload_to_ppa(self):
        # Arbitrary people cannot upload to a PPA.
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        ssp = self.factory.makeSuiteSourcePackage()
        self.assertRaises(
            CannotUploadToArchive, verify_upload, person, ssp, ppa)

    def test_owner_can_upload_to_ppa(self):
        # If the archive is a PPA, and you own it, then you can upload pretty
        # much anything to it.
        team = self.factory.makeTeam()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA, owner=team)
        person = self.factory.makePerson()
        removeSecurityProxy(team).addMember(person, team.teamowner)
        ssp = self.factory.makeSuiteSourcePackage()
        self.assertCanUpload(person, ssp, ppa)

    # XXX: Why doesn't nascentupload:verify_acl() check to see if the signer
    # is allowed to upload the specific package?

    # XXX: What's the next test to write?


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
