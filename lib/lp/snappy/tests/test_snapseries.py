# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap series."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from zope.component import getUtility

from lp.services.features.testing import FeatureFixture
from lp.services.webapp.interfaces import OAuthPermission
from lp.snappy.interfaces.snap import SNAP_TESTING_FLAGS
from lp.snappy.interfaces.snapseries import (
    ISnapSeries,
    ISnapSeriesSet,
    NoSuchSnapSeries,
    )
from lp.testing import (
    admin_logged_in,
    api_url,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.pages import webservice_for_person


class TestSnapSeries(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSnapSeries, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_implements_interface(self):
        # SnapSeries implements ISnapSeries.
        snap_series = self.factory.makeSnapSeries()
        self.assertProvides(snap_series, ISnapSeries)

    def test_new_no_usable_distro_series(self):
        snap_series = self.factory.makeSnapSeries()
        self.assertContentEqual([], snap_series.usable_distro_series)

    def test_set_usable_distro_series(self):
        dses = [self.factory.makeDistroSeries() for _ in range(3)]
        snap_series = self.factory.makeSnapSeries()
        snap_series.usable_distro_series = [dses[0]]
        self.assertContentEqual([dses[0]], snap_series.usable_distro_series)
        snap_series.usable_distro_series = dses
        self.assertContentEqual(dses, snap_series.usable_distro_series)
        snap_series.usable_distro_series = []
        self.assertContentEqual([], snap_series.usable_distro_series)


class TestSnapSeriesSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def setUp(self):
        super(TestSnapSeriesSet, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_getByName(self):
        snap_series = self.factory.makeSnapSeries(name="foo")
        self.factory.makeSnapSeries()
        snap_series_set = getUtility(ISnapSeriesSet)
        self.assertEqual(snap_series, snap_series_set.getByName("foo"))
        self.assertRaises(NoSuchSnapSeries, snap_series_set.getByName, "bar")

    def test_getByDistroSeries(self):
        dses = [self.factory.makeDistroSeries() for _ in range(3)]
        snap_serieses = [self.factory.makeSnapSeries() for _ in range(3)]
        snap_serieses[0].usable_distro_series = dses
        snap_serieses[1].usable_distro_series = [dses[0], dses[1]]
        snap_serieses[2].usable_distro_series = [dses[1], dses[2]]
        snap_series_set = getUtility(ISnapSeriesSet)
        self.assertContentEqual(
            [snap_serieses[0], snap_serieses[1]],
            snap_series_set.getByDistroSeries(dses[0]))
        self.assertContentEqual(
            snap_serieses, snap_series_set.getByDistroSeries(dses[1]))
        self.assertContentEqual(
            [snap_serieses[0], snap_serieses[2]],
            snap_series_set.getByDistroSeries(dses[2]))

    def test_getAll(self):
        snap_serieses = [self.factory.makeSnapSeries() for _ in range(3)]
        self.assertContentEqual(
            snap_serieses, getUtility(ISnapSeriesSet).getAll())


class TestSnapSeriesWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapSeriesWebservice, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_new_unpriv(self):
        # An unprivileged user cannot create a SnapSeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+snap-series", "new",
            name="dummy", display_name="dummy", status="Experimental")
        self.assertEqual(401, response.status)

    def test_new(self):
        # A registry expert can create a SnapSeries.
        person = self.factory.makeRegistryExpert()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snap-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(201, response.status)
        snap_series = webservice.get(response.getHeader("Location")).jsonBody()
        with person_logged_in(person):
            self.assertEqual(
                webservice.getAbsoluteUrl(api_url(person)),
                snap_series["registrant_link"])
            self.assertEqual("dummy", snap_series["name"])
            self.assertEqual("Dummy", snap_series["display_name"])
            self.assertEqual("Experimental", snap_series["status"])

    def test_new_duplicate_name(self):
        # An attempt to create a SnapSeries with a duplicate name is rejected.
        person = self.factory.makeRegistryExpert()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snap-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(201, response.status)
        response = webservice.named_post(
            "/+snap-series", "new",
            name="dummy", display_name="Dummy", status="Experimental")
        self.assertEqual(400, response.status)
        self.assertEqual(
            "name: dummy is already in use by another series.", response.body)

    def test_getByName(self):
        # lp.snap_serieses.getByName returns a matching SnapSeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with admin_logged_in():
            self.factory.makeSnapSeries(name="dummy")
        response = webservice.named_get(
            "/+snap-series", "getByName", name="dummy")
        self.assertEqual(200, response.status)
        self.assertEqual("dummy", response.jsonBody()["name"])

    def test_getByName_missing(self):
        # lp.snap_serieses.getByName returns 404 for a non-existent SnapSeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_get(
            "/+snap-series", "getByName", name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual("No such snap series: 'nonexistent'.", response.body)

    def test_getByDistroSeries(self):
        # lp.snap_serieses.getByDistroSeries returns a collection of
        # matching SnapSeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with admin_logged_in():
            dses = [self.factory.makeDistroSeries() for _ in range(3)]
            ds_urls = [api_url(ds) for ds in dses]
            snap_serieses = [
                self.factory.makeSnapSeries(name="ss-%d" % i)
                for i in range(3)]
            snap_serieses[0].usable_distro_series = dses
            snap_serieses[1].usable_distro_series = [dses[0], dses[1]]
            snap_serieses[2].usable_distro_series = [dses[1], dses[2]]
        for ds_url, expected_snap_series_names in (
                (ds_urls[0], ["ss-0", "ss-1"]),
                (ds_urls[1], ["ss-0", "ss-1", "ss-2"]),
                (ds_urls[2], ["ss-0", "ss-2"])):
            response = webservice.named_get(
                "/+snap-series", "getByDistroSeries", distro_series=ds_url)
            self.assertEqual(200, response.status)
            self.assertContentEqual(
                expected_snap_series_names,
                [entry["name"] for entry in response.jsonBody()["entries"]])

    def test_collection(self):
        # lp.snap_serieses is a collection of all SnapSeries.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with admin_logged_in():
            for i in range(3):
                self.factory.makeSnapSeries(name="ss-%d" % i)
        response = webservice.get("/+snap-series")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ["ss-0", "ss-1", "ss-2"],
            [entry["name"] for entry in response.jsonBody()["entries"]])
