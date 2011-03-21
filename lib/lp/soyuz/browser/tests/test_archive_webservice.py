# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import unittest

from lazr.restfulclient.errors import HTTPError

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.soyuz.enums import ArchivePurpose
from lp.testing import (
    celebrity_logged_in,
    launchpadlib_for,
    TestCaseWithFactory,
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
