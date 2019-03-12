# Copyright 2019 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test bases for snaps."""

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
from lp.snappy.interfaces.snapbase import (
    CannotDeleteSnapBase,
    ISnapBase,
    ISnapBaseSet,
    NoSuchSnapBase,
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


class TestSnapBase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_implements_interface(self):
        # SnapBase implements ISnapBase.
        snap_base = self.factory.makeSnapBase()
        self.assertProvides(snap_base, ISnapBase)

    def test_new_not_default(self):
        snap_base = self.factory.makeSnapBase()
        self.assertFalse(snap_base.is_default)

    def test_anonymous(self):
        # Anyone can view an `ISnapBase`.
        snap_base = self.factory.makeSnapBase()
        authz = getAdapter(snap_base, IAuthorization, name="launchpad.View")
        self.assertTrue(authz.checkUnauthenticated())

    def test_destroySelf(self):
        snap_base = self.factory.makeSnapBase()
        snap_base_name = snap_base.name
        snap_base_set = getUtility(ISnapBaseSet)
        self.assertEqual(snap_base, snap_base_set.getByName(snap_base_name))
        snap_base.destroySelf()
        self.assertRaises(
            NoSuchSnapBase, snap_base_set.getByName, snap_base_name)

    def test_destroySelf_refuses_default(self):
        snap_base = self.factory.makeSnapBase()
        getUtility(ISnapBaseSet).setDefault(snap_base)
        self.assertRaises(CannotDeleteSnapBase, snap_base.destroySelf)


class TestSnapBaseSet(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_getByName(self):
        snap_base_set = getUtility(ISnapBaseSet)
        snap_base = self.factory.makeSnapBase(name="foo")
        self.factory.makeSnapBase()
        self.assertEqual(snap_base, snap_base_set.getByName("foo"))
        self.assertRaises(NoSuchSnapBase, snap_base_set.getByName, "bar")

    def test_getDefault(self):
        snap_base_set = getUtility(ISnapBaseSet)
        snap_base = self.factory.makeSnapBase()
        self.factory.makeSnapBase()
        self.assertIsNone(snap_base_set.getDefault())
        snap_base_set.setDefault(snap_base)
        self.assertEqual(snap_base, snap_base_set.getDefault())

    def test_setDefault(self):
        snap_base_set = getUtility(ISnapBaseSet)
        snap_bases = [self.factory.makeSnapBase() for _ in range(3)]
        snap_base_set.setDefault(snap_bases[0])
        self.assertEqual(
            [True, False, False],
            [snap_base.is_default for snap_base in snap_bases])
        snap_base_set.setDefault(snap_bases[1])
        self.assertEqual(
            [False, True, False],
            [snap_base.is_default for snap_base in snap_bases])
        snap_base_set.setDefault(None)
        self.assertEqual(
            [False, False, False],
            [snap_base.is_default for snap_base in snap_bases])

    def test_getAll(self):
        snap_bases = [self.factory.makeSnapBase() for _ in range(3)]
        self.assertContentEqual(snap_bases, getUtility(ISnapBaseSet).getAll())


class TestSnapBaseWebservice(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_new_unpriv(self):
        # An unprivileged user cannot create a SnapBase.
        person = self.factory.makePerson()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+snap-bases", "new",
            name="dummy", display_name="Dummy", distro_series=distroseries_url,
            build_channels={"snapcraft": "stable"})
        self.assertEqual(401, response.status)

    def test_new(self):
        # A registry expert can create a SnapBase.
        person = self.factory.makeRegistryExpert()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snap-bases", "new",
            name="dummy", display_name="Dummy", distro_series=distroseries_url,
            build_channels={"snapcraft": "stable"})
        self.assertEqual(201, response.status)
        snap_base = webservice.get(response.getHeader("Location")).jsonBody()
        with person_logged_in(person):
            self.assertThat(snap_base, ContainsDict({
                "registrant_link": Equals(
                    webservice.getAbsoluteUrl(api_url(person))),
                "name": Equals("dummy"),
                "display_name": Equals("Dummy"),
                "distro_series_link": Equals(
                    webservice.getAbsoluteUrl(distroseries_url)),
                "build_channels": Equals({"snapcraft": "stable"}),
                "is_default": Is(False),
                }))

    def test_new_duplicate_name(self):
        # An attempt to create a SnapBase with a duplicate name is rejected.
        person = self.factory.makeRegistryExpert()
        distroseries = self.factory.makeDistroSeries()
        distroseries_url = api_url(distroseries)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_post(
            "/+snap-bases", "new",
            name="dummy", display_name="Dummy", distro_series=distroseries_url,
            build_channels={"snapcraft": "stable"})
        self.assertEqual(201, response.status)
        response = webservice.named_post(
            "/+snap-bases", "new",
            name="dummy", display_name="Dummy", distro_series=distroseries_url,
            build_channels={"snapcraft": "stable"})
        self.assertEqual(400, response.status)
        self.assertEqual(
            "name: dummy is already in use by another base.", response.body)

    def test_getByName(self):
        # lp.snap_bases.getByName returns a matching SnapBase.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with celebrity_logged_in("registry_experts"):
            self.factory.makeSnapBase(name="dummy")
        response = webservice.named_get(
            "/+snap-bases", "getByName", name="dummy")
        self.assertEqual(200, response.status)
        self.assertEqual("dummy", response.jsonBody()["name"])

    def test_getByName_missing(self):
        # lp.snap_bases.getByName returns 404 for a non-existent SnapBase.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        logout()
        response = webservice.named_get(
            "/+snap-bases", "getByName", name="nonexistent")
        self.assertEqual(404, response.status)
        self.assertEqual("No such base: 'nonexistent'.", response.body)

    def test_getDefault(self):
        # lp.snap_bases.getDefault returns the default SnapBase, if any.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_get("/+snap-bases", "getDefault")
        self.assertEqual(200, response.status)
        self.assertIsNone(response.jsonBody())
        with celebrity_logged_in("registry_experts"):
            getUtility(ISnapBaseSet).setDefault(
                self.factory.makeSnapBase(name="default-base"))
            self.factory.makeSnapBase()
        response = webservice.named_get("/+snap-bases", "getDefault")
        self.assertEqual(200, response.status)
        self.assertEqual("default-base", response.jsonBody()["name"])

    def test_setDefault_unpriv(self):
        # An unprivileged user cannot set the default SnapBase.
        person = self.factory.makePerson()
        with celebrity_logged_in("registry_experts"):
            snap_base = self.factory.makeSnapBase()
            snap_base_url = api_url(snap_base)
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+snap-bases", "setDefault", snap_base=snap_base_url)
        self.assertEqual(401, response.status)

    def test_setDefault(self):
        # A registry expert can set the default SnapBase.
        person = self.factory.makeRegistryExpert()
        with person_logged_in(person):
            snap_bases = [self.factory.makeSnapBase() for _ in range(3)]
            snap_base_urls = [api_url(snap_base) for snap_base in snap_bases]
        webservice = webservice_for_person(
            person, permission=OAuthPermission.WRITE_PUBLIC)
        webservice.default_api_version = "devel"
        response = webservice.named_post(
            "/+snap-bases", "setDefault", snap_base=snap_base_urls[0])
        self.assertEqual(200, response.status)
        with person_logged_in(person):
            self.assertEqual(
                snap_bases[0], getUtility(ISnapBaseSet).getDefault())
        response = webservice.named_post(
            "/+snap-bases", "setDefault", snap_base=snap_base_urls[1])
        self.assertEqual(200, response.status)
        with person_logged_in(person):
            self.assertEqual(
                snap_bases[1], getUtility(ISnapBaseSet).getDefault())

    def test_collection(self):
        # lp.snap_bases is a collection of all SnapBases.
        person = self.factory.makePerson()
        webservice = webservice_for_person(
            person, permission=OAuthPermission.READ_PUBLIC)
        webservice.default_api_version = "devel"
        with celebrity_logged_in("registry_experts"):
            for i in range(3):
                self.factory.makeSnapBase(name="base-%d" % i)
        response = webservice.get("/+snap-bases")
        self.assertEqual(200, response.status)
        self.assertContentEqual(
            ["base-0", "base-1", "base-2"],
            [entry["name"] for entry in response.jsonBody()["entries"]])
