# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the permissions for uploading to an archive."""

__metaclass__ = type

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer

from lp.registry.interfaces.series import SeriesStatus
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.interfaces.archive import ArchivePurpose
from lp.soyuz.interfaces.archivepermission import IArchivePermissionSet
from lp.testing import TestCaseWithFactory


class TestComponents(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_no_components_for_arbitrary_person(self):
        # By default, a person cannot upload to any component of an archive.
        archive = self.factory.makeArchive()
        person = self.factory.makePerson()
        self.assertEqual(set(),
            set(archive.getComponentsForUploader(person)))

    def test_components_for_person_with_permissions(self):
        # If a person has been explicitly granted upload permissions to a
        # particular component, then those components are included in
        # IArchive.getComponentsForUploader.
        archive = self.factory.makeArchive()
        component = self.factory.makeComponent()
        person = self.factory.makePerson()
        # Only admins or techboard members can add permissions normally. That
        # restriction isn't relevant to this test.
        ap_set = removeSecurityProxy(getUtility(IArchivePermissionSet))
        ap = ap_set.newComponentUploader(archive, person, component)
        self.assertEqual(set([ap]),
            set(archive.getComponentsForUploader(person)))


class TestPermission(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        permission_set = getUtility(IArchivePermissionSet)
        # Only admins or techboard members can add permissions normally. That
        # restriction isn't relevant to these tests.
        self.permission_set = removeSecurityProxy(permission_set)

    def assertCanUpload(self, person, spn, archive, component,
                        strict_component=True, distroseries=None):
        """Assert that 'person' can upload 'spn' to 'archive'."""
        # For now, just check that doesn't raise an exception.
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries(
                distribution=archive.distribution)
        pocket = PackagePublishingPocket.RELEASE
        self.assertIs(
            None,
            archive.checkUpload(
                person, distroseries, spn, component, pocket,
                strict_component))

    def assertCannotUpload(self, reason, person, spn, archive, component,
                           distroseries=None):
        """Assert that 'person' cannot upload to the archive.

        :param reason: The expected reason for not being able to upload. A
            string.
        :param person: The person trying to upload.
        :param spn: The `ISourcePackageName` being uploaded to. None if the
            package does not yet exist.
        :param archive: The `IArchive` being uploaded to.
        :param component: The IComponent to which the package belongs.
        :param distroseries: The upload's target distro series.
        """
        if distroseries is None:
            distroseries = self.factory.makeDistroSeries()
        pocket = PackagePublishingPocket.RELEASE
        exception = archive.checkUpload(
            person, distroseries, spn, component, pocket)
        self.assertEqual(reason, str(exception))

    def test_random_person_cannot_upload_to_ppa(self):
        # Arbitrary people cannot upload to a PPA.
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        spn = self.factory.makeSourcePackageName()
        self.assertCannotUpload(
            'Signer has no upload rights to this PPA.',
            person, spn, ppa, None)

    def test_owner_can_upload_to_ppa(self):
        # If the archive is a PPA, and you own it, then you can upload pretty
        # much anything to it.
        team = self.factory.makeTeam()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA, owner=team)
        person = self.factory.makePerson()
        removeSecurityProxy(team).addMember(person, team.teamowner)
        spn = self.factory.makeSourcePackageName()
        self.assertCanUpload(person, spn, ppa, None)

    def test_owner_can_upload_to_ppa_no_sourcepackage(self):
        # The owner can upload to PPAs even if the source package doesn't
        # exist yet.
        team = self.factory.makeTeam()
        ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA, owner=team)
        person = self.factory.makePerson()
        removeSecurityProxy(team).addMember(person, team.teamowner)
        self.assertCanUpload(person, None, ppa, None)

    def test_can_upload_to_ppa_for_old_series(self):
        # You can upload whatever you want to a PPA, regardless of the upload
        # policy.
        person = self.factory.makePerson()
        ppa = self.factory.makeArchive(
            purpose=ArchivePurpose.PPA, owner=person)
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries(
            status=SeriesStatus.CURRENT)
        self.assertCanUpload(
            person, spn, ppa, None, distroseries=distroseries)

    def test_arbitrary_person_cannot_upload_to_primary_archive(self):
        # By default, you can't upload to the primary archive.
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        spn = self.factory.makeSourcePackageName()
        self.assertCannotUpload(
            ("The signer of this package is lacking the upload rights for "
             "the source package, component or package set in question."),
            person, spn, archive, None)

    def test_package_specific_rights(self):
        # A person can be granted specific rights for uploading a package,
        # based only on the source package name. If they have these rights,
        # they can upload to the package.
        person = self.factory.makePerson()
        spn = self.factory.makeSourcePackageName()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        # We can't use a PPA, because they have a different logic for
        # permissions. We can't create an arbitrary archive, because there's
        # only one primary archive per distro.
        self.permission_set.newPackageUploader(archive, person, spn)
        self.assertCanUpload(person, spn, archive, None)

    def test_packageset_specific_rights(self):
        # A person with rights to upload to the package set can upload the
        # package set to the archive.
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        spn = self.factory.makeSourcePackageName()
        distroseries = self.factory.makeDistroSeries()
        package_set = self.factory.makePackageset(
            packages=[spn], distroseries=distroseries)
        self.permission_set.newPackagesetUploader(
            archive, person, package_set)
        self.assertCanUpload(
            person, spn, archive, None, distroseries=distroseries)

    def test_packageset_wrong_distroseries(self):
        # A person with rights to upload to the package set in distro
        # series K may not upload with these same rights to a different
        # distro series L.
        distroseries_K = self.factory.makeDistroRelease()
        distroseries_L = self.factory.makeDistroRelease()
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        spn = self.factory.makeSourcePackageName()
        package_set = self.factory.makePackageset(
            packages=[spn], distroseries=distroseries_K)
        self.permission_set.newPackagesetUploader(
            archive, person, package_set)
        self.assertCanUpload(
            person, spn, archive, None, distroseries=distroseries_K)
        self.assertCannotUpload(
            ("The signer of this package is lacking the upload rights for "
             "the source package, component or package set in question."),
            person, spn, archive, None, distroseries=distroseries_L)

    def test_component_rights(self):
        # A person allowed to upload to a particular component of an archive
        # can upload basically whatever they want to that component.
        person = self.factory.makePerson()
        spn = self.factory.makeSourcePackageName()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        component = self.factory.makeComponent()
        self.permission_set.newComponentUploader(archive, person, component)
        self.assertCanUpload(person, spn, archive, component)

    def test_incorrect_component_rights(self):
        # Even if a person has upload rights for a particular component in an
        # archive, it doesn't mean they have upload rights for everything in
        # that archive.
        person = self.factory.makePerson()
        spn = self.factory.makeSourcePackageName()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        permitted_component = self.factory.makeComponent()
        forbidden_component = self.factory.makeComponent()
        self.permission_set.newComponentUploader(
            archive, person, permitted_component)
        self.assertCannotUpload(
            u"Signer is not permitted to upload to the component '%s'." % (
                forbidden_component.name),
            person, spn, archive, forbidden_component)

    def test_component_rights_no_package(self):
        # A person allowed to upload to a particular component of an archive
        # can upload basically whatever they want to that component, even if
        # the package doesn't exist yet.
        person = self.factory.makePerson()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        component = self.factory.makeComponent()
        self.permission_set.newComponentUploader(archive, person, component)
        self.assertCanUpload(person, None, archive, component)

    def test_non_strict_component_rights(self):
        # If we aren't testing strict component access, then we only need to
        # have access to an arbitrary component.
        person = self.factory.makePerson()
        spn = self.factory.makeSourcePackageName()
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PRIMARY)
        component_a = self.factory.makeComponent()
        component_b = self.factory.makeComponent()
        self.permission_set.newComponentUploader(archive, person, component_b)
        self.assertCanUpload(
            person, spn, archive, component_a, strict_component=False)

    def test_cannot_upload_to_disabled_archive(self):
        spn = self.factory.makeSourcePackageName()
        archive = self.factory.makeArchive()
        removeSecurityProxy(archive).disable()
        component = self.factory.makeComponent()
        self.assertCannotUpload(u"%s is disabled." % (archive.displayname),
            archive.owner, spn, archive, component)
