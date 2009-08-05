# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the permissions for uploading to an archive."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer

from lp.archiveuploader.permission import CannotUploadToArchive, verify_upload
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
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

    def test_arbitrary_person_cannot_upload_to_primary_archive(self):
        # By default, you can't upload to the primary archive.
        person = self.factory.makePerson()
        ssp = self.factory.makeSuiteSourcePackage()
        archive = ssp.distribution.main_archive
        self.assertRaises(
            CannotUploadToArchive, verify_upload, person, ssp, archive)

    def test_package_specific_rights(self):
        # A person can be granted specific rights for uploading a package,
        # based only on the source package name. If they have these rights,
        # they can upload to the package.
        person = self.factory.makePerson()
        ssp = self.factory.makeSuiteSourcePackage()
        # We can't use a PPA, because they have a different logic for
        # permissions. We can't create an arbitrary archive, because there's
        # only one primary archive per distro.
        archive = ssp.distribution.main_archive
        permission_set = getUtility(IArchivePermissionSet)
        removeSecurityProxy(permission_set).newPackageUploader(
            archive, person, ssp.sourcepackagename)
        self.assertCanUpload(person, ssp, archive)

    def test_packageset_specific_rights(self):
        # A person with rights to upload to the package set can upload the
        # package set to the archive.
        person = self.factory.makePerson()
        ssp = self.factory.makeSuiteSourcePackage()
        archive = ssp.distribution.main_archive
        package_set = self.factory.makePackageSet(
            packages=[ssp.sourcepackagename])
        permission_set = getUtility(IArchivePermissionSet)
        removeSecurityProxy(permission_set).newPackagesetUploader(
            archive, person, package_set)
        self.assertCanUpload(person, ssp, archive)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
