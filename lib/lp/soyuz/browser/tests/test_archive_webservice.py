# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import timedelta

from lazr.restfulclient.errors import (
    BadRequest,
    HTTPError,
    NotFound,
    Unauthorized as LRUnauthorized,
    )
from testtools import ExpectedException
from testtools.matchers import MatchesStructure
import transaction
from zope.component import getUtility

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.webapp.interfaces import OAuthPermission
from lp.soyuz.enums import (
    ArchivePermissionType,
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.packagecopyjob import IPlainPackageCopyJobSource
from lp.soyuz.model.archivepermission import ArchivePermission
from lp.testing import (
    admin_logged_in,
    api_url,
    launchpadlib_for,
    person_logged_in,
    record_two_runs,
    TestCaseWithFactory,
    WebServiceTestCase,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import HasQueryCount
from lp.testing.pages import (
    LaunchpadWebServiceCaller,
    webservice_for_person,
    )


class TestArchiveWebservice(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestArchiveWebservice, self).setUp()
        with admin_logged_in():
            self.archive = self.factory.makeArchive(
                purpose=ArchivePurpose.PRIMARY)
            distroseries = self.factory.makeDistroSeries(
                distribution=self.archive.distribution)
            person = self.factory.makePerson()
            distro_name = self.archive.distribution.name
            distroseries_name = distroseries.name
            person_name = person.name

        self.launchpad = launchpadlib_for(
            "archive test", "salgado", "WRITE_PUBLIC")
        self.distribution = self.launchpad.distributions[distro_name]
        self.distroseries = self.distribution.getSeries(
            name_or_version=distroseries_name)
        self.main_archive = self.distribution.main_archive
        self.person = self.launchpad.people[person_name]

    def test_checkUpload_bad_pocket(self):
        # Make sure a 403 error and not an OOPS is returned when
        # CannotUploadToPocket is raised when calling checkUpload.

        # When we're on Python 2.7, this code will be much nicer as
        # assertRaises is a context manager so you can do something like
        # with self.assertRaises(HTTPError) as cm; do_something
        # .... then you have cm.exception available.
        def _do_check():
            self.main_archive.checkUpload(
                distroseries=self.distroseries,
                sourcepackagename="mozilla-firefox",
                pocket="Updates",
                component="restricted",
                person=self.person)

        e = self.assertRaises(HTTPError, _do_check)

        self.assertEqual(403, e.response.status)
        self.assertIn(
            "Not permitted to upload to the UPDATES pocket in a series "
            "in the 'DEVELOPMENT' state.", e.content)

    def test_getAllPermissions_constant_query_count(self):
        # getAllPermissions has a query count constant in the number of
        # permissions and people.
        def create_permission():
            with admin_logged_in():
                ArchivePermission(
                    archive=self.archive, person=self.factory.makePerson(),
                    component=getUtility(IComponentSet)["main"],
                    permission=ArchivePermissionType.UPLOAD)

        def get_permissions():
            list(self.main_archive.getAllPermissions())

        recorder1, recorder2 = record_two_runs(
            get_permissions, create_permission, 1)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))

    def test_delete(self):
        with admin_logged_in():
            ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
            ppa_url = api_url(ppa)
            ws = webservice_for_person(
                ppa.owner, permission=OAuthPermission.WRITE_PRIVATE)

        # DELETE on an archive resource doesn't actually remove it
        # immediately, but it asks the publisher to delete it later.
        self.assertEqual(
            'Active',
            ws.get(ppa_url, api_version='devel').jsonBody()['status'])
        self.assertEqual(200, ws.delete(ppa_url, api_version='devel').status)
        self.assertEqual(
            'Deleting',
            ws.get(ppa_url, api_version='devel').jsonBody()['status'])

        # Deleting the PPA again fails.
        self.assertThat(
            ws.delete(ppa_url, api_version='devel'),
            MatchesStructure.byEquality(
                status=400, body="Archive already deleted."))

    def test_delete_is_restricted(self):
        with admin_logged_in():
            ppa = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
            ppa_url = api_url(ppa)
            ws = webservice_for_person(
                self.factory.makePerson(),
                permission=OAuthPermission.WRITE_PRIVATE)

        # A random user can't delete someone else's PPA.
        self.assertEqual(401, ws.delete(ppa_url, api_version='devel').status)


class TestExternalDependencies(WebServiceTestCase):

    def test_external_dependencies_random_user(self):
        """Normal users can look but not touch."""
        archive = self.factory.makeArchive()
        transaction.commit()
        ws_archive = self.wsObject(archive)
        self.assertIs(None, ws_archive.external_dependencies)
        ws_archive.external_dependencies = "random"
        with ExpectedException(LRUnauthorized, '.*'):
            ws_archive.lp_save()

    def test_external_dependencies_owner(self):
        """Normal archive owners can look but not touch."""
        archive = self.factory.makeArchive()
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        self.assertIs(None, ws_archive.external_dependencies)
        ws_archive.external_dependencies = "random"
        with ExpectedException(LRUnauthorized, '.*'):
            ws_archive.lp_save()

    def test_external_dependencies_ppa_owner_invalid(self):
        """PPA admins can look and touch."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        archive = self.factory.makeArchive(owner=ppa_admin)
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        self.assertIs(None, ws_archive.external_dependencies)
        ws_archive.external_dependencies = "random"
        regex = '(\n|.)*Invalid external dependencies(\n|.)*'
        with ExpectedException(BadRequest, regex):
            ws_archive.lp_save()

    def test_external_dependencies_ppa_owner_valid(self):
        """PPA admins can look and touch."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        archive = self.factory.makeArchive(owner=ppa_admin)
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        self.assertIs(None, ws_archive.external_dependencies)
        ws_archive.external_dependencies = (
            "deb http://example.org suite components")
        ws_archive.lp_save()


class TestArchiveDependencies(WebServiceTestCase):

    def test_addArchiveDependency_random_user(self):
        """Normal users cannot add archive dependencies."""
        archive = self.factory.makeArchive()
        dependency = self.factory.makeArchive()
        transaction.commit()
        ws_archive = self.wsObject(archive)
        ws_dependency = self.wsObject(dependency)
        self.assertContentEqual([], ws_archive.dependencies)
        failure_regex = '(.|\n)*addArchiveDependency.*launchpad.Edit(.|\n)*'
        with ExpectedException(LRUnauthorized, failure_regex):
            dependency = ws_archive.addArchiveDependency(
                dependency=ws_dependency, pocket='Release', component='main')

    def test_addArchiveDependency_owner(self):
        """Normal users cannot add archive dependencies."""
        archive = self.factory.makeArchive()
        dependency = self.factory.makeArchive()
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        ws_dependency = self.wsObject(dependency)
        self.assertContentEqual([], ws_archive.dependencies)
        with ExpectedException(NotFound, '(.|\n)*asdf(.|\n)*'):
            ws_archive.addArchiveDependency(
                dependency=ws_dependency, pocket='Release', component='asdf')
        dependency = ws_archive.addArchiveDependency(
            dependency=ws_dependency, pocket='Release', component='main')
        self.assertContentEqual([dependency], ws_archive.dependencies)

    def test_addArchiveDependency_invalid(self):
        """Invalid requests generate a BadRequest error."""
        archive = self.factory.makeArchive()
        dependency = self.factory.makeArchive()
        with person_logged_in(archive.owner):
            archive.addArchiveDependency(
                dependency, PackagePublishingPocket.RELEASE)
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        ws_dependency = self.wsObject(dependency)
        expected_re = '(.|\n)*This dependency is already registered(.|\n)*'
        with ExpectedException(BadRequest, expected_re):
            ws_archive.addArchiveDependency(
                dependency=ws_dependency, pocket='Release')

    def test_removeArchiveDependency_random_user(self):
        """Normal users can remove archive dependencies."""
        archive = self.factory.makeArchive()
        dependency = self.factory.makeArchive()
        with person_logged_in(archive.owner):
            archive.addArchiveDependency(
                dependency, PackagePublishingPocket.RELEASE)
        transaction.commit()
        ws_archive = self.wsObject(archive)
        ws_dependency = self.wsObject(dependency)
        failure_regex = '(.|\n)*remove.*Dependency.*launchpad.Edit(.|\n)*'
        with ExpectedException(LRUnauthorized, failure_regex):
            ws_archive.removeArchiveDependency(dependency=ws_dependency)

    def test_removeArchiveDependency_owner(self):
        """Normal users can remove archive dependencies."""
        archive = self.factory.makeArchive()
        dependency = self.factory.makeArchive()
        with person_logged_in(archive.owner):
            archive.addArchiveDependency(
                dependency, PackagePublishingPocket.RELEASE)
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        ws_dependency = self.wsObject(dependency)
        ws_archive.removeArchiveDependency(dependency=ws_dependency)
        self.assertContentEqual([], ws_archive.dependencies)


class TestProcessors(WebServiceTestCase):
    """Test the enabled_restricted_processors property and methods."""

    def test_erpNotAvailableInBeta(self):
        """The enabled_restricted_processors property is not in beta."""
        self.ws_version = 'beta'
        archive = self.factory.makeArchive()
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        transaction.commit()
        ws_archive = self.wsObject(archive, user=ppa_admin)
        expected_re = (
            "(.|\n)*object has no attribute "
            "'enabled_restricted_processors'(.|\n)*")
        with ExpectedException(AttributeError, expected_re):
            ws_archive.enabled_restricted_processors

    def test_erpAvailableInDevel(self):
        """The enabled_restricted_processors property is in devel."""
        self.ws_version = 'devel'
        archive = self.factory.makeArchive()
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        transaction.commit()
        ws_archive = self.wsObject(archive, user=ppa_admin)
        self.assertContentEqual([], ws_archive.enabled_restricted_processors)

    def test_processors(self):
        """Attributes about processors are available."""
        self.ws_version = 'devel'
        self.factory.makeProcessor(
            'new-arm', 'New ARM Title', 'New ARM Description')
        transaction.commit()
        ws_proc = self.service.processors.getByName(name='new-arm')
        self.assertEqual('new-arm', ws_proc.name)
        self.assertEqual('New ARM Title', ws_proc.title)
        self.assertEqual('New ARM Description', ws_proc.description)

    def setProcessors(self, user, archive_url, names):
        ws = webservice_for_person(
            user, permission=OAuthPermission.WRITE_PUBLIC)
        return ws.named_post(
            archive_url, 'setProcessors',
            processors=['/+processors/%s' % name for name in names],
            api_version='devel')

    def assertProcessors(self, user, archive_url, names):
        body = webservice_for_person(user).get(
            archive_url + '/processors', api_version='devel').jsonBody()
        self.assertContentEqual(
            names, [entry['name'] for entry in body['entries']])

    def test_setProcessors_admin(self):
        """An admin can add a new processor to the enabled restricted set."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        self.factory.makeProcessor(
            'arm', 'ARM', 'ARM', restricted=True, build_by_default=False)
        ppa_url = api_url(self.factory.makeArchive(purpose=ArchivePurpose.PPA))
        self.assertProcessors(ppa_admin, ppa_url, ['386', 'hppa', 'amd64'])

        response = self.setProcessors(ppa_admin, ppa_url, ['386', 'arm'])
        self.assertEqual(200, response.status)
        self.assertProcessors(ppa_admin, ppa_url, ['386', 'arm'])

    def test_setProcessors_non_owner_forbidden(self):
        """Only PPA admins and archive owners can call setProcessors."""
        self.factory.makeProcessor(
            'unrestricted', 'Unrestricted', 'Unrestricted', restricted=False,
            build_by_default=False)
        ppa_url = api_url(self.factory.makeArchive(purpose=ArchivePurpose.PPA))

        response = self.setProcessors(
            self.factory.makePerson(), ppa_url, ['386', 'unrestricted'])
        self.assertEqual(401, response.status)

    def test_setProcessors_owner(self):
        """The archive owner can enable/disable unrestricted processors."""
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        ppa_url = api_url(archive)
        owner = archive.owner
        self.assertProcessors(owner, ppa_url, ['386', 'hppa', 'amd64'])

        response = self.setProcessors(owner, ppa_url, ['386'])
        self.assertEqual(200, response.status)
        self.assertProcessors(owner, ppa_url, ['386'])

        response = self.setProcessors(owner, ppa_url, ['386', 'amd64'])
        self.assertEqual(200, response.status)
        self.assertProcessors(owner, ppa_url, ['386', 'amd64'])

    def test_setProcessors_owner_restricted_forbidden(self):
        """The archive owner cannot enable/disable restricted processors."""
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        self.factory.makeProcessor(
            'arm', 'ARM', 'ARM', restricted=True, build_by_default=False)
        archive = self.factory.makeArchive(purpose=ArchivePurpose.PPA)
        ppa_url = api_url(archive)
        owner = archive.owner

        response = self.setProcessors(owner, ppa_url, ['386', 'arm'])
        self.assertEqual(403, response.status)

        # If a PPA admin enables arm, the owner cannot disable it.
        response = self.setProcessors(ppa_admin, ppa_url, ['386', 'arm'])
        self.assertEqual(200, response.status)
        self.assertProcessors(owner, ppa_url, ['386', 'arm'])

        response = self.setProcessors(owner, ppa_url, ['386'])
        self.assertEqual(403, response.status)

    def test_enableRestrictedProcessor(self):
        """A new processor can be added to the enabled restricted set."""
        self.ws_version = 'devel'
        archive = self.factory.makeArchive()
        self.factory.makeProcessor(
            name='arm', restricted=True, build_by_default=False)
        ppa_admin_team = getUtility(ILaunchpadCelebrities).ppa_admin
        ppa_admin = self.factory.makePerson(member_of=[ppa_admin_team])
        transaction.commit()
        ws_arm = self.service.processors.getByName(name='arm')
        ws_archive = self.wsObject(archive, user=ppa_admin)
        self.assertContentEqual([], ws_archive.enabled_restricted_processors)
        ws_archive.enableRestrictedProcessor(processor=ws_arm)
        self.assertContentEqual(
            [ws_arm], ws_archive.enabled_restricted_processors)

    def test_enableRestrictedProcessor_owner(self):
        """A new processor can be added to the enabled restricted set.

        An unauthorized user, even the archive owner, is not allowed.
        """
        self.ws_version = 'devel'
        archive = self.factory.makeArchive()
        self.factory.makeProcessor(
            name='arm', restricted=True, build_by_default=False)
        transaction.commit()
        ws_arm = self.service.processors.getByName(name='arm')
        ws_archive = self.wsObject(archive, user=archive.owner)
        self.assertContentEqual([], ws_archive.enabled_restricted_processors)
        expected_re = (
            "(.|\n)*'launchpad\.Admin'(.|\n)*")
        with ExpectedException(LRUnauthorized, expected_re):
            ws_archive.enableRestrictedProcessor(processor=ws_arm)

    def test_enableRestrictedProcessor_nonPrivUser(self):
        """A new processor can be added to the enabled restricted set.

        An unauthorized user, some regular user, is not allowed.
        """
        self.ws_version = 'devel'
        archive = self.factory.makeArchive()
        self.factory.makeProcessor(
            name='arm', restricted=True, build_by_default=False)
        just_some_guy = self.factory.makePerson()
        transaction.commit()
        ws_arm = self.service.processors.getByName(name='arm')
        ws_archive = self.wsObject(archive, user=just_some_guy)
        self.assertContentEqual([], ws_archive.enabled_restricted_processors)
        expected_re = (
            "(.|\n)*'launchpad\.Admin'(.|\n)*")
        with ExpectedException(LRUnauthorized, expected_re):
            ws_archive.enableRestrictedProcessor(processor=ws_arm)


class TestCopyPackage(WebServiceTestCase):
    """Webservice test cases for the copyPackage/copyPackages methods"""

    def setup_data(self):
        self.ws_version = "devel"
        uploader_dude = self.factory.makePerson()
        sponsored_dude = self.factory.makePerson()
        source_archive = self.factory.makeArchive()
        target_archive = self.factory.makeArchive(
            purpose=ArchivePurpose.PRIMARY)
        source = self.factory.makeSourcePackagePublishingHistory(
            archive=source_archive, status=PackagePublishingStatus.PUBLISHED)
        source_name = source.source_package_name
        version = source.source_package_version
        to_pocket = PackagePublishingPocket.RELEASE
        to_series = self.factory.makeDistroSeries(
            distribution=target_archive.distribution)
        with person_logged_in(target_archive.owner):
            target_archive.newComponentUploader(uploader_dude, "universe")
        transaction.commit()
        return (source, source_archive, source_name, target_archive,
                to_pocket, to_series, uploader_dude, sponsored_dude, version)

    def test_copyPackage(self):
        """Basic smoke test"""
        (source, source_archive, source_name, target_archive, to_pocket,
         to_series, uploader_dude, sponsored_dude,
         version) = self.setup_data()

        ws_target_archive = self.wsObject(target_archive, user=uploader_dude)
        ws_source_archive = self.wsObject(source_archive)
        ws_sponsored_dude = self.wsObject(sponsored_dude)

        ws_target_archive.copyPackage(
            source_name=source_name, version=version,
            from_archive=ws_source_archive, to_pocket=to_pocket.name,
            to_series=to_series.name, include_binaries=False,
            sponsored=ws_sponsored_dude)
        transaction.commit()

        job_source = getUtility(IPlainPackageCopyJobSource)
        copy_job = job_source.getActiveJobs(target_archive).one()
        self.assertEqual(target_archive, copy_job.target_archive)

    def test_copyPackages(self):
        """Basic smoke test"""
        (source, source_archive, source_name, target_archive, to_pocket,
         to_series, uploader_dude, sponsored_dude,
         version) = self.setup_data()

        ws_target_archive = self.wsObject(target_archive, user=uploader_dude)
        ws_source_archive = self.wsObject(source_archive)
        ws_sponsored_dude = self.wsObject(sponsored_dude)

        ws_target_archive.copyPackages(
            source_names=[source_name], from_archive=ws_source_archive,
            to_pocket=to_pocket.name, to_series=to_series.name,
            from_series=source.distroseries.name, include_binaries=False,
            sponsored=ws_sponsored_dude)
        transaction.commit()

        job_source = getUtility(IPlainPackageCopyJobSource)
        copy_job = job_source.getActiveJobs(target_archive).one()
        self.assertEqual(target_archive, copy_job.target_archive)


class TestgetPublishedBinaries(WebServiceTestCase):
    """test getPublishedSources."""

    def setUp(self):
        super(TestgetPublishedBinaries, self).setUp()
        self.ws_version = 'beta'
        self.person = self.factory.makePerson()
        self.archive = self.factory.makeArchive()

    def test_getPublishedBinaries(self):
        self.factory.makeBinaryPackagePublishingHistory(archive=self.archive)
        ws_archive = self.wsObject(self.archive, user=self.person)
        self.assertEqual(1, len(ws_archive.getPublishedBinaries()))

    def test_getPublishedBinaries_created_since_date(self):
        datecreated = self.factory.getUniqueDate()
        later_date = datecreated + timedelta(minutes=1)
        self.factory.makeBinaryPackagePublishingHistory(
                archive=self.archive, datecreated=datecreated)
        ws_archive = self.wsObject(self.archive, user=self.person)
        publications = ws_archive.getPublishedBinaries(
                created_since_date=later_date)
        self.assertEqual(0, len(publications))

    def test_getPublishedBinaries_no_ordering(self):
        self.factory.makeBinaryPackagePublishingHistory(archive=self.archive)
        self.factory.makeBinaryPackagePublishingHistory(archive=self.archive)
        ws_archive = self.wsObject(self.archive, user=self.person)
        publications = ws_archive.getPublishedBinaries(ordered=False)
        self.assertEqual(2, len(publications))

    def test_getPublishedBinaries_query_count(self):
        # getPublishedBinaries has a query count constant in the number of
        # packages returned.
        archive_url = api_url(self.archive)

        def create_bpph():
            with admin_logged_in():
                self.factory.makeBinaryPackagePublishingHistory(
                    archive=self.archive)

        def get_binaries():
            LaunchpadWebServiceCaller('consumer', '').named_get(
                archive_url, 'getPublishedBinaries').jsonBody()

        recorder1, recorder2 = record_two_runs(get_binaries, create_bpph, 1)
        self.assertThat(recorder2, HasQueryCount.byEquality(recorder1))


class TestremoveCopyNotification(WebServiceTestCase):
    """Test removeCopyNotification."""

    def setUp(self):
        super(TestremoveCopyNotification, self).setUp()
        self.ws_version = 'devel'
        self.person = self.factory.makePerson()
        self.archive = self.factory.makeArchive(owner=self.person)

    def test_removeCopyNotification(self):
        distroseries = self.factory.makeDistroSeries()
        source_archive = self.factory.makeArchive(distroseries.distribution)
        requester = self.factory.makePerson()
        source = getUtility(IPlainPackageCopyJobSource)
        job = source.create(
            package_name="foo", source_archive=source_archive,
            target_archive=self.archive, target_distroseries=distroseries,
            target_pocket=PackagePublishingPocket.RELEASE,
            package_version="1.0-1", include_binaries=True,
            requester=requester)
        job.start()
        job.fail()

        ws_archive = self.wsObject(self.archive, user=self.person)
        ws_archive.removeCopyNotification(job_id=job.id)
        transaction.commit()

        source = getUtility(IPlainPackageCopyJobSource)
        self.assertEqual(
            None, source.getIncompleteJobsForArchive(self.archive).any())


class TestArchiveSet(TestCaseWithFactory):
    """Test ArchiveSet.getByReference."""

    layer = DatabaseFunctionalLayer

    def test_getByReference(self):
        random = self.factory.makePerson()
        body = LaunchpadWebServiceCaller('consumer', '').named_get(
            '/archives', 'getByReference', reference='ubuntu',
            api_version='devel').jsonBody()
        self.assertEqual(body['reference'], 'ubuntu')
        body = webservice_for_person(random).named_get(
            '/archives', 'getByReference', reference='ubuntu',
            api_version='devel').jsonBody()
        self.assertEqual(body['reference'], 'ubuntu')

    def test_getByReference_ppa(self):
        body = LaunchpadWebServiceCaller('consumer', '').named_get(
            '/archives', 'getByReference', reference='~cprov/ubuntu/ppa',
            api_version='devel').jsonBody()
        self.assertEqual(body['reference'], '~cprov/ubuntu/ppa')

    def test_getByReference_invalid(self):
        body = LaunchpadWebServiceCaller('consumer', '').named_get(
            '/archives', 'getByReference', reference='~cprov/ubuntu',
            api_version='devel').jsonBody()
        self.assertIs(None, body)

    def test_getByReference_private(self):
        with admin_logged_in():
            archive = self.factory.makeArchive(private=True)
            owner = archive.owner
            reference = archive.reference
            random = self.factory.makePerson()
        body = LaunchpadWebServiceCaller('consumer', '').named_get(
            '/archives', 'getByReference', reference=reference,
            api_version='devel').jsonBody()
        self.assertIs(None, body)
        body = webservice_for_person(random).named_get(
            '/archives', 'getByReference', reference=reference,
            api_version='devel').jsonBody()
        self.assertIs(None, body)
        body = webservice_for_person(owner).named_get(
            '/archives', 'getByReference', reference=reference,
            api_version='devel').jsonBody()
        self.assertEqual(body['reference'], reference)
