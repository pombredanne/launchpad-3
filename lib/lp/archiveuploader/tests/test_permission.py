# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the permissions for uploading to an archive."""

__metaclass__ = type

import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer

from lp.archiveuploader.permission import (
    CannotUploadToArchive, components_valid_for, verify_upload)
from lp.registry.interfaces.gpg import GPGKeyAlgorithm, IGPGKeySet
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestComponents(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_no_components_for_arbitrary_person(self):
        # By default, a person cannot upload to any component of an archive.
        archive = self.factory.makeArchive()
        person = self.factory.makePerson()
        self.assertEqual(set(), components_valid_for(archive, person))

    def test_components_for_person_with_permissions(self):
        # If a person has been explicitly granted upload permissions to a
        # particular component, then those components are included in
        # components_valid_for.
        archive = self.factory.makeArchive()
        component = self.factory.makeComponent()
        person = self.factory.makePerson()
        ap_set = removeSecurityProxy(getUtility(IArchivePermissionSet))
        ap_set.newComponentUploader(archive, person, component)
        self.assertEqual(
            set([component]), components_valid_for(archive, person))


class TestPermission(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def assertCanUpload(self, person, ssp, archive, strict_component=True):
        """Assert that 'person' can upload 'ssp' to 'archive'."""
        # For now, just check that doesn't raise an exception.
        component = ssp.sourcepackage.latest_published_component
        verify_upload(
            person, ssp.sourcepackagename, archive, component,
            strict_component)

    def makeGPGKey(self, owner):
        """Give 'owner' a crappy GPG key for the purposes of testing."""
        return getUtility(IGPGKeySet).new(
            owner.id,
            keyid='DEADBEEF',
            fingerprint='A' * 40,
            keysize=self.factory.getUniqueInteger(),
            algorithm=GPGKeyAlgorithm.R,
            active=True,
            can_encrypt=False)

    def setComponent(self, archive, suite_sourcepackage, component):
        """Set the component of `suite_sourcepackage` to `component`.

        :param archive: The `IArchive` that the package is being uploaded to.
        :param suite_sourcepackage: An `ISuiteSourcePackage` that the
            component is being set on.
        :param component: An `IComponent` to upload the package to, thus
            setting the latest component.
        """
        stp = SoyuzTestPublisher()
        stp.factory = self.factory
        stp.person = self.factory.makePerson()
        self.makeGPGKey(stp.person)
        return stp.getPubSource(
            sourcename=suite_sourcepackage.sourcepackagename.name,
            component=component.name,
            distroseries=suite_sourcepackage.distroseries,
            archive=archive,
            status=PackagePublishingStatus.PUBLISHED,
            do_upload=False)

    def test_random_person_cannot_upload_to_ppa(self):
        # Arbitrary people cannot upload to a PPA.
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        ssp = self.factory.makeSuiteSourcePackage()
        self.assertRaises(
            CannotUploadToArchive,
            verify_upload, person, ssp.sourcepackagename, ppa, None)

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
            CannotUploadToArchive,
            verify_upload, person, ssp.sourcepackagename, archive, None)

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

    def test_component_rights(self):
        # A person allowed to upload to a particular component of an archive
        # can upload basically whatever they want to that component.
        person = self.factory.makePerson()
        ssp = self.factory.makeSuiteSourcePackage()
        archive = ssp.distribution.main_archive
        component = self.factory.makeComponent()
        self.setComponent(archive, ssp, component)
        permission_set = getUtility(IArchivePermissionSet)
        removeSecurityProxy(permission_set).newComponentUploader(
            archive, person, component)
        self.assertCanUpload(person, ssp, archive)

    def test_non_strict_component_rights(self):
        # If we aren't testing strict component access, then we only need to
        # have access to an arbitrary component.
        person = self.factory.makePerson()
        ssp = self.factory.makeSuiteSourcePackage()
        archive = ssp.distribution.main_archive
        component_a = self.factory.makeComponent()
        self.setComponent(archive, ssp, component_a)
        permission_set = getUtility(IArchivePermissionSet)
        component_b = self.factory.makeComponent()
        removeSecurityProxy(permission_set).newComponentUploader(
            archive, person, component_b)
        self.assertCanUpload(person, ssp, archive, strict_component=False)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
