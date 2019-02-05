# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test base snaps."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from testtools.matchers import (
    ContainsDict,
    Equals,
    Is,
    )
from zope.component import (
    getAdapter,
    getUtility,
    )

from lp.app.interfaces.security import IAuthorization
from lp.services.webapp.interfaces import OAuthPermission
from lp.snappy.interfaces.basesnap import (
    CannotDeleteBaseSnap,
    IBaseSnap,
    IBaseSnapSet,
    NoSuchBaseSnap,
    )
from lp.testing import (
    api_url,
    celebrity_logged_in,
    logout,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    ZopelessDatabaseLayer,
    )
from lp.testing.pages import webservice_for_person


class TestBaseSnap(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_implements_interface(self):
        # BaseSnap implements IBaseSnap.
        base_snap = self.factory.makeBaseSnap()
        self.assertProvides(base_snap, IBaseSnap)

    def test_new_not_default(self):
        base_snap = self.factory.makeBaseSnap()
        self.assertFalse(base_snap.is_default)

    def test_anonymous(self):
        # Anyone can view an `IBaseSnap`.
        base_snap = self.factory.makeBaseSnap()
        authz = getAdapter(base_snap, IAuthorization, name="launchpad.View")
        self.assertTrue(authz.checkUnauthenticated())

    def test_destroySelf(self):
        base_snap = self.factory.makeBaseSnap()
        base_snap_name = base_snap.name
        base_snap_set = getUtility(IBaseSnapSet)
        self.assertEqual(base_snap, base_snap_set.getByName(base_snap_name))
        base_snap.destroySelf()
        self.assertRaises(
            NoSuchBaseSnap, base_snap_set.getByName, base_snap_name)

    def test_destroySelf_refuses_default(self):
        base_snap = self.factory.makeBaseSnap()
        getUtility(IBaseSnapSet).setDefault(base_snap)
        self.assertRaises(CannotDeleteBaseSnap, base_snap.destroySelf)


class TestBaseSnapSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_getByName(self):
        base_snap_set = getUtility(IBaseSnapSet)
        base_snap = self.factory.makeBaseSnap(name="foo")
        self.factory.makeBaseSnap()
        self.assertEqual(base_snap, base_snap_set.getByName("foo"))
        self.assertRaises(NoSuchBaseSnap, base_snap_set.getByName, "bar")

    def test_getDefault(self):
        base_snap_set = getUtility(IBaseSnapSet)
        base_snap = self.factory.makeBaseSnap()
        self.factory.makeBaseSnap()
        self.assertIsNone(base_snap_set.getDefault())
        base_snap_set.setDefault(base_snap)
        self.assertEqual(base_snap, base_snap_set.getDefault())

    def test_setDefault(self):
        base_snap_set = getUtility(IBaseSnapSet)
        base_snaps = [self.factory.makeBaseSnap() for _ in range(3)]
        base_snap_set.setDefault(base_snaps[0])
        self.assertEqual(
            [True, False, False],
            [base_snap.is_default for base_snap in base_snaps])
        base_snap_set.setDefault(base_snaps[1])
        self.assertEqual(
            [False, True, False],
            [base_snap.is_default for base_snap in base_snaps])
        base_snap_set.setDefault(None)
        self.assertEqual(
            [False, False, False],
            [base_snap.is_default for base_snap in base_snaps])

    def test_getAll(self):
        base_snaps = [self.factory.makeBaseSnap() for _ in range(3)]
        self.assertContentEqual(base_snaps, getUtility(IBaseSnapSet).getAll())


class TestBaseSnapWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_new_unpriv(self):
        # An unprivileged user cannot create a BaseSnap.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+base-snaps", "new",
            name="dummy", display_name="Dummy",
            distro_series=distroseries_url, channels={"snapcraft": "stable"})
        self.assertEqual(401, response.status)

    def test_new(self):
        # A registry expert can create a BaseSnap.
        person = self.factory.makeRegistryExpert()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+base-snaps", "new",
            name="dummy", display_name="Dummy",
            distro_series=distroseries_url, channels={"snapcraft": "stable"})
        self.assertEqual(201, response.status)
        base_snap = webservice.get(response.getHeader("Location")).jsonBody()
        with person_logged_in(person):
            self.assertThat(base_snap, ContainsDict({
                "registrant_link": Equals(
                    webservice.getAbsoluteUrl(api_url(person))),
                "name": Equals("dummy"),
                "display_name": Equals("Dummy"),
                "distro_series_link": Equals(
                    webservice.getAbsoluteUrl(distroseries_url)),
                "channels": Equals({"snapcraft": "stable"}),
                "is_default": Is(False),
                }))

    def test_new_duplicate_name(self):
        # An attempt to create a BaseSnap with a duplicate name is rejected.
        person = self.factory.makeRegistryExpert()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+base-snaps", "new",
            name="dummy", display_name="Dummy",
            distro_series=distroseries_url, channels={"snapcraft": "stable"})
        self.assertEqual(201, response.status)
        response = webservice.named_post(
            "/+base-snaps", "new",
            name="dummy", display_name="Dummy",
            distro_series=distroseries_url, channels={"snapcraft": "stable"})
        self.assertEqual(400, response.status)
        self.assertEqual(
            "name: dummy is already in use by another base snap.",
            response.body)

    def test_getByName(self):
        # lp.base_snaps.getByName returns a matching BaseSnap.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with celebrity_logged_in("registry_experts"):
            self.factory.makeBaseSnap(name="dummy")
        response = webservice.named_get(
            "/+base-snaps", "getByName", name="dummy")
        self.assertEqual(200, response.status)
        self.assertEqual("dummy", response.jsonBody()["name"])

    def test_getByName_missing(self):
        # lp.base_snaps.getByName returns 404 for a non-existent BaseSnap.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_get(
            "/+base-snaps", "getByName", name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual("No such base snap: 'nonexistent'.", response.body)

    def test_getDefault(self):
        # lp.base_snaps.getDefault returns the default BaseSnap, if any.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get("/+base-snaps", "getDefault")
        self.assertEqual(200, response.status)
        self.assertIsNone(response.jsonBody())
        with celebrity_logged_in("registry_experts"):
            getUtility(IBaseSnapSet).setDefault(
                self.factory.makeBaseSnap(name="default-base"))
            self.factory.makeBaseSnap()
        response = webservice.named_get("/+base-snaps", "getDefault")
        self.assertEqual(200, response.status)
        self.assertEqual("default-base", response.jsonBody()["name"])

    def test_setDefault_unpriv(self):
        # An unprivileged user cannot set the default BaseSnap.
        person = self.factory.makePerson()
        with celebrity_logged_in("registry_experts"):
            base_snap = self.factory.makeBaseSnap()
            base_snap_url = api_url(base_snap)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+base-snaps", "setDefault", base_snap=base_snap_url)
        self.assertEqual(401, response.status)

    def test_setDefault(self):
        # A registry expert can set the default BaseSnap.
        person = self.factory.makeRegistryExpert()
        with person_logged_in(person):
            base_snaps = [self.factory.makeBaseSnap() for _ in range(3)]
            base_snap_urls = [api_url(base_snap) for base_snap in base_snaps]
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+base-snaps", "setDefault", base_snap=base_snap_urls[0])
        self.assertEqual(200, response.status)
        with person_logged_in(person):
            self.assertEqual(
                base_snaps[0], getUtility(IBaseSnapSet).getDefault())
        response = webservice.named_post(
            "/+base-snaps", "setDefault", base_snap=base_snap_urls[1])
        self.assertEqual(200, response.status)
        with person_logged_in(person):
            self.assertEqual(
                base_snaps[1], getUtility(IBaseSnapSet).getDefault())

    def test_collection(self):
        # lp.base_snaps is a collection of all BaseSnaps.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with celebrity_logged_in("registry_experts"):
            for i in range(3):
                self.factory.makeBaseSnap(name="base-%d" % i)
        response = webservice.get("/+base-snaps")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ["base-0", "base-1", "base-2"],
            [entry["name"] for entry in response.jsonBody()["entries"]])
