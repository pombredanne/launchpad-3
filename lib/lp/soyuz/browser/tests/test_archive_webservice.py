# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lazr.restfulclient.errors import (
    BadRequest,
    HTTPError,
    Unauthorized as LRUnauthorized,
)
from testtools import ExpectedException
import transaction
from zope.component import getUtility

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    celebrity_logged_in,
    launchpadlib_for,
    person_logged_in,
    TestCaseWithFactory,
    WebServiceTestCase,
    )


class TestArchiveWebservice(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        with celebrity_logged_in('admin'):
            archive = self.factory.makeArchive(
                purpose=ArchivePurpose.PRIMARY)
            distroseries = self.factory.makeDistroSeries(
                distribution=archive.distribution)
            person = self.factory.makePerson()
            distro_name = archive.distribution.name
            distroseries_name = distroseries.name
            person_name = person.name

        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

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

    def test_external_dependencies_commercial_owner_invalid(self):
        """Commercial admins can look and touch."""
        commercial = getUtility(ILaunchpadCelebrities).commercial_admin
        owner = self.factory.makePerson(member_of=[commercial])
        archive = self.factory.makeArchive(owner=owner)
        transaction.commit()
        ws_archive = self.wsObject(archive, archive.owner)
        self.assertIs(None, ws_archive.external_dependencies)
        ws_archive.external_dependencies = "random"
        regex = '(\n|.)*Invalid external dependencies(\n|.)*'
        with ExpectedException(BadRequest, regex):
            ws_archive.lp_save()

    def test_external_dependencies_commercial_owner_valid(self):
        """Commercial admins can look and touch."""
        commercial = getUtility(ILaunchpadCelebrities).commercial_admin
        owner = self.factory.makePerson(member_of=[commercial])
        archive = self.factory.makeArchive(owner=owner)
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
        with ExpectedException(BadRequest, '(.|\n)*asdf(.|\n)*'):
            ws_archive.addArchiveDependency(
                dependency=ws_dependency, pocket='Release', component='asdf')
        dependency = ws_archive.addArchiveDependency(
            dependency=ws_dependency, pocket='Release', component='main')
        self.assertContentEqual([dependency], ws_archive.dependencies)

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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
