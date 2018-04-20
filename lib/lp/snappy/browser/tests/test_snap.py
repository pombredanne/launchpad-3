# Copyright 2015-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import json
import re
from urllib2 import HTTPError
from urlparse import (
    parse_qs,
    urlsplit,
    )

from fixtures import FakeLogger
from httmock import (
    all_requests,
    HTTMock,
    )
from mechanize import LinkNotFoundError
import mock
from pymacaroons import Macaroon
import pytz
import soupmatchers
from testtools.matchers import (
    MatchesSetwise,
    MatchesStructure,
    )
import transaction
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized

from lp.app.enums import InformationType
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.code.errors import (
    GitRepositoryBlobNotFound,
    GitRepositoryScanFault,
    )
from lp.code.tests.helpers import GitHostingFixture
from lp.registry.enums import PersonVisibility
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
from lp.services.config import config
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.snappy.browser.snap import (
    SnapAdminView,
    SnapEditView,
    SnapView,
    )
from lp.snappy.interfaces.snap import (
    CannotModifySnapProcessor,
    ISnapSet,
    SNAP_PRIVATE_FEATURE_FLAG,
    SNAP_TESTING_FLAGS,
    SnapPrivateFeatureDisabled,
    )
from lp.snappy.interfaces.snappyseries import ISnappyDistroSeriesSet
from lp.snappy.interfaces.snapstoreclient import ISnapStoreClient
from lp.testing import (
    admin_logged_in,
    BrowserTestCase,
    login,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
from lp.testing.fakemethod import FakeMethod
from lp.testing.fixture import ZopeUtilityFixture
from lp.testing.layers import (
    DatabaseFunctionalLayer,
    LaunchpadFunctionalLayer,
    )
from lp.testing.matchers import (
    MatchesPickerText,
    MatchesTagText,
    )
from lp.testing.pages import (
    extract_text,
    find_main_content,
    find_tag_by_id,
    find_tags_by_class,
    get_feedback_messages,
    )
from lp.testing.publication import test_traverse
from lp.testing.views import (
    create_initialized_view,
    create_view,
    )


class TestSnapNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapNavigation, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, name="snap")
        self.assertEqual(
            "http://launchpad.dev/~person/+snap/snap", canonical_url(snap))

    def test_snap(self):
        snap = self.factory.makeSnap()
        obj, _, _ = test_traverse(
            "http://launchpad.dev/~%s/+snap/%s" % (snap.owner.name, snap.name))
        self.assertEqual(snap, obj)


class TestSnapViewsFeatureFlag(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_private_feature_flag_disabled(self):
        # Without a private_snap feature flag, we will not create Snaps for
        # private contexts.
        self.snap_store_client = FakeMethod()
        self.snap_store_client.listChannels = FakeMethod(result=[])
        self.useFixture(
            ZopeUtilityFixture(self.snap_store_client, ISnapStoreClient))
        owner = self.factory.makePerson()
        branch = self.factory.makeAnyBranch(
            owner=owner, information_type=InformationType.USERDATA)
        with person_logged_in(owner):
            self.assertRaises(
                SnapPrivateFeatureDisabled, create_initialized_view,
                branch, "+new-snap")


class BaseTestSnapView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(BaseTestSnapView, self).setUp()
        self.useFixture(FeatureFixture(SNAP_TESTING_FLAGS))
        self.useFixture(FakeLogger())
        self.snap_store_client = FakeMethod()
        self.snap_store_client.listChannels = FakeMethod(result=[
            {"name": "stable", "display_name": "Stable"},
            {"name": "edge", "display_name": "Edge"},
            ])
        self.snap_store_client.requestPackageUploadPermission = (
            getUtility(ISnapStoreClient).requestPackageUploadPermission)
        self.useFixture(
            ZopeUtilityFixture(self.snap_store_client, ISnapStoreClient))
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")


class TestSnapAddView(BaseTestSnapView):

    def setUp(self):
        super(TestSnapAddView, self).setUp()
        self.distroseries = self.factory.makeUbuntuDistroSeries(
            version="13.10")
        with admin_logged_in():
            self.snappyseries = self.factory.makeSnappySeries(
                preferred_distro_series=self.distroseries)

    def setUpDistroSeries(self):
        """Set up a distroseries with some available processors."""
        distroseries = self.factory.makeUbuntuDistroSeries()
        processor_names = ["386", "amd64", "hppa"]
        for name in processor_names:
            processor = getUtility(IProcessorSet).getByName(name)
            self.factory.makeDistroArchSeries(
                distroseries=distroseries, architecturetag=name,
                processor=processor)
        with admin_logged_in():
            self.factory.makeSnappySeries(preferred_distro_series=distroseries)
        return distroseries

    def assertProcessorControls(self, processors_control, enabled, disabled):
        matchers = [
            MatchesStructure.byEquality(optionValue=name, disabled=False)
            for name in enabled]
        matchers.extend([
            MatchesStructure.byEquality(optionValue=name, disabled=True)
            for name in disabled])
        self.assertThat(processors_control.controls, MatchesSetwise(*matchers))

    def test_initial_store_distro_series(self):
        # The initial store_distro_series uses the preferred distribution
        # series for the latest snappy series.
        lts = self.factory.makeUbuntuDistroSeries(
            version="16.04", status=SeriesStatus.CURRENT)
        current = self.factory.makeUbuntuDistroSeries(
            version="16.10", status=SeriesStatus.CURRENT)
        with admin_logged_in():
            self.factory.makeSnappySeries(usable_distro_series=[lts, current])
            newest = self.factory.makeSnappySeries(
                preferred_distro_series=lts,
                usable_distro_series=[lts, current])
        branch = self.factory.makeAnyBranch()
        with person_logged_in(self.person):
            view = create_initialized_view(branch, "+new-snap")
        self.assertThat(
            view.initial_values["store_distro_series"],
            MatchesStructure.byEquality(
                snappy_series=newest, distro_series=lts))

    def test_create_new_snap_not_logged_in(self):
        branch = self.factory.makeAnyBranch()
        self.assertRaises(
            Unauthorized, self.getViewBrowser, branch, view_name="+new-snap",
            no_login=True)

    def test_create_new_snap_bzr(self):
        branch = self.factory.makeAnyBranch()
        source_display = branch.display_name
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("snap-name", extract_text(content.h1))
        self.assertThat(
            "Test Person", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit snap package" %
            self.distroseries.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Source:\n%s\nEdit snap package" % source_display,
            MatchesTagText(content, "source"))
        self.assertThat(
            "Source tarball:\n"
            "Builds of this snap package will not build a source tarball.\n"
            "Edit snap package",
            MatchesTagText(content, "source_tarball"))
        self.assertThat(
            "Build schedule:\n(?)\nBuilt on request\nEdit snap package\n",
            MatchesTagText(content, "auto_build"))
        self.assertThat(
            "Source archive for automatic builds:\n\nEdit snap package\n",
            MatchesTagText(content, "auto_build_archive"))
        self.assertThat(
            "Pocket for automatic builds:\n\nEdit snap package",
            MatchesTagText(content, "auto_build_pocket"))
        self.assertThat(
            "Builds of this snap package are not automatically uploaded to "
            "the store.\nEdit snap package",
            MatchesTagText(content, "store_upload"))

    def test_create_new_snap_git(self):
        self.useFixture(GitHostingFixture(blob=""))
        [git_ref] = self.factory.makeGitRefs()
        source_display = git_ref.display_name
        browser = self.getViewBrowser(
            git_ref, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("snap-name", extract_text(content.h1))
        self.assertThat(
            "Test Person", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit snap package" %
            self.distroseries.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Source:\n%s\nEdit snap package" % source_display,
            MatchesTagText(content, "source"))
        self.assertThat(
            "Source tarball:\n"
            "Builds of this snap package will not build a source tarball.\n"
            "Edit snap package",
            MatchesTagText(content, "source_tarball"))
        self.assertThat(
            "Build schedule:\n(?)\nBuilt on request\nEdit snap package\n",
            MatchesTagText(content, "auto_build"))
        self.assertThat(
            "Source archive for automatic builds:\n\nEdit snap package\n",
            MatchesTagText(content, "auto_build_archive"))
        self.assertThat(
            "Pocket for automatic builds:\n\nEdit snap package",
            MatchesTagText(content, "auto_build_pocket"))
        self.assertThat(
            "Builds of this snap package are not automatically uploaded to "
            "the store.\nEdit snap package",
            MatchesTagText(content, "store_upload"))

    def test_create_new_snap_users_teams_as_owner_options(self):
        # Teams that the user is in are options for the snap package owner.
        self.factory.makeTeam(
            name="test-team", displayname="Test Team", members=[self.person])
        branch = self.factory.makeAnyBranch()
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        options = browser.getControl("Owner").displayOptions
        self.assertEqual(
            ["Test Person (test-person)", "Test Team (test-team)"],
            sorted(str(option) for option in options))

    def test_create_new_snap_public(self):
        # Public owner implies public snap.
        branch = self.factory.makeAnyBranch()

        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "public-snap"
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("public-snap", extract_text(content.h1))
        self.assertEqual(
            'This snap contains Public information',
            extract_text(find_tag_by_id(browser.contents, "privacy"))
        )

    def test_create_new_snap_private_link(self):
        # Link for create new snaps for private content is only displayed
        # if the 'snap.allow_private' is enabled.
        login_person(self.person)
        branch = self.factory.makeAnyBranch(
            owner=self.person,
            information_type=InformationType.USERDATA)

        with FeatureFixture({SNAP_PRIVATE_FEATURE_FLAG: ""}):
            browser = self.getViewBrowser(branch, user=self.person)
            self.assertRaises(
                LinkNotFoundError, browser.getLink, "Create snap package")
        with FeatureFixture(SNAP_TESTING_FLAGS):
            browser = self.getViewBrowser(branch, user=self.person)
            browser.getLink("Create snap package")

    def test_create_new_snap_private(self):
        # Private teams will automatically create private snaps.
        login_person(self.person)
        self.factory.makeTeam(
            name='super-private', owner=self.person,
            visibility=PersonVisibility.PRIVATE)
        branch = self.factory.makeAnyBranch()

        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "private-snap"
        browser.getControl("Owner").value = ['super-private']
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("private-snap", extract_text(content.h1))
        self.assertEqual(
            'This snap contains Private information',
            extract_text(find_tag_by_id(browser.contents, "privacy"))
        )

    def test_create_new_snap_source_tarball(self):
        # We can create a new snap and ask for it to build a source tarball.
        branch = self.factory.makeAnyBranch()
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl("Build source tarball").selected = True
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertThat(
            "Source tarball:\n"
            "Builds of this snap package will also build a source tarball.\n"
            "Edit snap package",
            MatchesTagText(content, "source_tarball"))

    def test_create_new_snap_auto_build(self):
        # Creating a new snap and asking for it to be automatically built
        # sets all the appropriate fields.
        branch = self.factory.makeAnyBranch()
        archive = self.factory.makeArchive()
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl(
            "Automatically build when branch changes").selected = True
        browser.getControl("PPA").click()
        browser.getControl(name="field.auto_build_archive.ppa").value = (
            archive.reference)
        browser.getControl("Pocket for automatic builds").value = ["SECURITY"]
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertThat(
            "Build schedule:\n(?)\nBuilt automatically\nEdit snap package\n",
            MatchesTagText(content, "auto_build"))
        self.assertThat(
            "Source archive for automatic builds:\n%s\nEdit snap package\n" %
            archive.displayname,
            MatchesTagText(content, "auto_build_archive"))
        self.assertThat(
            "Pocket for automatic builds:\nSecurity\nEdit snap package",
            MatchesTagText(content, "auto_build_pocket"))

    def test_create_new_snap_store_upload(self):
        # Creating a new snap and asking for it to be automatically uploaded
        # to the store sets all the appropriate fields and redirects to SSO
        # for authorization.
        branch = self.factory.makeAnyBranch()
        view_url = canonical_url(branch, view_name="+new-snap")
        browser = self.getNonRedirectingBrowser(url=view_url, user=self.person)
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl("Automatically upload to store").selected = True
        browser.getControl("Registered store package name").value = (
            "store-name")
        self.assertFalse(browser.getControl("Stable").selected)
        browser.getControl(name="field.store_channels.track").value = "track"
        browser.getControl("Edge").selected = True
        root_macaroon = Macaroon()
        root_macaroon.add_third_party_caveat(
            urlsplit(config.launchpad.openid_provider_root).netloc, "",
            "dummy")
        root_macaroon_raw = root_macaroon.serialize()

        @all_requests
        def handler(url, request):
            self.request = request
            return {
                "status_code": 200,
                "content": {"macaroon": root_macaroon_raw},
                }

        self.pushConfig("snappy", store_url="http://sca.example/")
        with HTTMock(handler):
            redirection = self.assertRaises(
                HTTPError, browser.getControl("Create snap package").click)
        login_person(self.person)
        snap = getUtility(ISnapSet).getByName(self.person, "snap-name")
        self.assertThat(snap, MatchesStructure.byEquality(
            owner=self.person, distro_series=self.distroseries,
            name="snap-name", source=branch, store_upload=True,
            store_series=self.snappyseries, store_name="store-name",
            store_secrets={"root": root_macaroon_raw},
            store_channels=["track/edge"]))
        self.assertThat(self.request, MatchesStructure.byEquality(
            url="http://sca.example/dev/api/acl/", method="POST"))
        expected_body = {
            "packages": [{
                "name": "store-name",
                "series": self.snappyseries.name,
                }],
            "permissions": ["package_upload"],
            }
        self.assertEqual(expected_body, json.loads(self.request.body))
        self.assertEqual(303, redirection.code)
        parsed_location = urlsplit(redirection.hdrs["Location"])
        self.assertEqual(
            urlsplit(
                canonical_url(snap, rootsite="code") +
                "/+authorize/+login")[:3],
            parsed_location[:3])
        expected_args = {
            "discharge_macaroon_action": ["field.actions.complete"],
            "discharge_macaroon_field": ["field.discharge_macaroon"],
            "macaroon_caveat_id": ["dummy"],
            }
        self.assertEqual(expected_args, parse_qs(parsed_location[3]))

    def test_create_new_snap_display_processors(self):
        branch = self.factory.makeAnyBranch()
        self.setUpDistroSeries()
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(
            ["Intel 386 (386)", "AMD 64bit (amd64)", "HPPA Processor (hppa)"],
            [extract_text(option) for option in processors.displayOptions])
        self.assertContentEqual(["386", "amd64", "hppa"], processors.options)
        self.assertContentEqual(["386", "amd64", "hppa"], processors.value)

    def test_create_new_snap_display_restricted_processors(self):
        # A restricted processor is shown disabled in the UI.
        branch = self.factory.makeAnyBranch()
        distroseries = self.setUpDistroSeries()
        proc_armhf = self.factory.makeProcessor(
            name="armhf", restricted=True, build_by_default=False)
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="armhf",
            processor=proc_armhf)
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        processors = browser.getControl(name="field.processors")
        self.assertProcessorControls(
            processors, ["386", "amd64", "hppa"], ["armhf"])

    def test_create_new_snap_processors(self):
        branch = self.factory.makeAnyBranch()
        self.setUpDistroSeries()
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        processors = browser.getControl(name="field.processors")
        processors.value = ["386", "amd64"]
        browser.getControl(name="field.name").value = "snap-name"
        browser.getControl("Create snap package").click()
        login_person(self.person)
        snap = getUtility(ISnapSet).getByName(self.person, "snap-name")
        self.assertContentEqual(
            ["386", "amd64"], [proc.name for proc in snap.processors])

    def test_initial_name_extraction_git_snap_snapcraft_yaml(self):
        def getBlob(filename, *args, **kwargs):
            if filename == "snap/snapcraft.yaml":
                return "name: test-snap"
            else:
                raise GitRepositoryBlobNotFound("dummy", filename)

        [git_ref] = self.factory.makeGitRefs()
        git_ref.repository.getBlob = getBlob
        view = create_initialized_view(git_ref, "+new-snap")
        initial_values = view.initial_values
        self.assertIn('store_name', initial_values)
        self.assertEqual('test-snap', initial_values['store_name'])

    def test_initial_name_extraction_git_plain_snapcraft_yaml(self):
        def getBlob(filename, *args, **kwargs):
            if filename == "snapcraft.yaml":
                return "name: test-snap"
            else:
                raise GitRepositoryBlobNotFound("dummy", filename)

        [git_ref] = self.factory.makeGitRefs()
        git_ref.repository.getBlob = getBlob
        view = create_initialized_view(git_ref, "+new-snap")
        initial_values = view.initial_values
        self.assertIn('store_name', initial_values)
        self.assertEqual('test-snap', initial_values['store_name'])

    def test_initial_name_extraction_git_dot_snapcraft_yaml(self):
        def getBlob(filename, *args, **kwargs):
            if filename == ".snapcraft.yaml":
                return "name: test-snap"
            else:
                raise GitRepositoryBlobNotFound("dummy", filename)

        [git_ref] = self.factory.makeGitRefs()
        git_ref.repository.getBlob = getBlob
        view = create_initialized_view(git_ref, "+new-snap")
        initial_values = view.initial_values
        self.assertIn('store_name', initial_values)
        self.assertEqual('test-snap', initial_values['store_name'])

    def test_initial_name_extraction_git_repo_error(self):
        [git_ref] = self.factory.makeGitRefs()
        git_ref.repository.getBlob = FakeMethod(failure=GitRepositoryScanFault)
        view = create_initialized_view(git_ref, "+new-snap")
        initial_values = view.initial_values
        self.assertIn('store_name', initial_values)
        self.assertIsNone(initial_values['store_name'])

    def test_initial_name_extraction_git_invalid_data(self):
        for invalid_result in (None, 123, '', '[][]', '#name:test', ']'):
            [git_ref] = self.factory.makeGitRefs()
            git_ref.repository.getBlob = FakeMethod(result=invalid_result)
            view = create_initialized_view(git_ref, "+new-snap")
            initial_values = view.initial_values
            self.assertIn('store_name', initial_values)
            self.assertIsNone(initial_values['store_name'])

    def test_initial_name_extraction_git_safe_yaml(self):
        [git_ref] = self.factory.makeGitRefs()
        git_ref.repository.getBlob = FakeMethod(result='Malicious YAML!')
        view = create_initialized_view(git_ref, "+new-snap")
        with mock.patch('yaml.load') as unsafe_load:
            with mock.patch('yaml.safe_load') as safe_load:
                view.initial_values
        self.assertEqual(0, unsafe_load.call_count)
        self.assertEqual(1, safe_load.call_count)


class TestSnapAdminView(BaseTestSnapView):

    def test_unauthorized(self):
        # A non-admin user cannot administer a snap package.
        login_person(self.person)
        snap = self.factory.makeSnap(registrant=self.person)
        snap_url = canonical_url(snap)
        browser = self.getViewBrowser(snap, user=self.person)
        self.assertRaises(
            LinkNotFoundError, browser.getLink, "Administer snap package")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, snap_url + "/+admin",
            user=self.person)

    def test_admin_snap(self):
        # Admins can change require_virtualized, privacy, and allow_internet.
        login("admin@canonical.com")
        commercial_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).commercial_admin])
        login_person(self.person)
        snap = self.factory.makeSnap(registrant=self.person)
        self.assertTrue(snap.require_virtualized)
        self.assertFalse(snap.private)
        self.assertTrue(snap.allow_internet)

        browser = self.getViewBrowser(snap, user=commercial_admin)
        browser.getLink("Administer snap package").click()
        browser.getControl("Require virtualized builders").selected = False
        browser.getControl("Private").selected = True
        browser.getControl("Allow external network access").selected = False
        browser.getControl("Update snap package").click()

        login_person(self.person)
        self.assertFalse(snap.require_virtualized)
        self.assertTrue(snap.private)
        self.assertFalse(snap.allow_internet)

    def test_admin_snap_privacy_mismatch(self):
        # Cannot make snap public if it still contains private information.
        login_person(self.person)
        team = self.factory.makeTeam(
            owner=self.person, visibility=PersonVisibility.PRIVATE)
        snap = self.factory.makeSnap(
            registrant=self.person, owner=team, private=True)
        # Note that only LP admins or, in this case, commercial_admins
        # can reach this snap because it's owned by a private team.
        commercial_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).commercial_admin])
        browser = self.getViewBrowser(snap, user=commercial_admin)
        browser.getLink("Administer snap package").click()
        browser.getControl("Private").selected = False
        browser.getControl("Update snap package").click()
        self.assertEqual(
            'This snap contains private information and cannot be public.',
            extract_text(find_tags_by_class(browser.contents, "message")[1]))

    def test_admin_snap_sets_date_last_modified(self):
        # Administering a snap package sets the date_last_modified property.
        login("admin@canonical.com")
        ppa_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).ppa_admin])
        login_person(self.person)
        date_created = datetime(2000, 1, 1, tzinfo=pytz.UTC)
        snap = self.factory.makeSnap(
            registrant=self.person, date_created=date_created)
        login_person(ppa_admin)
        view = SnapAdminView(snap, LaunchpadTestRequest())
        view.initialize()
        view.request_action.success({"require_virtualized": False})
        self.assertSqlAttributeEqualsDate(snap, "date_last_modified", UTC_NOW)


class TestSnapEditView(BaseTestSnapView):

    def setUp(self):
        super(TestSnapEditView, self).setUp()
        self.distroseries = self.factory.makeUbuntuDistroSeries(
            version="13.10")
        with admin_logged_in():
            self.snappyseries = self.factory.makeSnappySeries(
                usable_distro_series=[self.distroseries])

    def test_initial_store_series(self):
        # The initial store_series is the newest that is usable for the
        # selected distroseries.
        development = self.factory.makeUbuntuDistroSeries(
            version="14.10", status=SeriesStatus.DEVELOPMENT)
        experimental = self.factory.makeUbuntuDistroSeries(
            version="15.04", status=SeriesStatus.EXPERIMENTAL)
        with admin_logged_in():
            self.factory.makeSnappySeries(
                usable_distro_series=[development, experimental])
            newest = self.factory.makeSnappySeries(
                usable_distro_series=[development])
            self.factory.makeSnappySeries(usable_distro_series=[experimental])
        snap = self.factory.makeSnap(distroseries=development)
        with person_logged_in(self.person):
            view = create_initialized_view(snap, "+edit")
        self.assertThat(
            view.initial_values["store_distro_series"],
            MatchesStructure.byEquality(
                snappy_series=newest, distro_series=development))

    def test_edit_snap(self):
        old_series = self.factory.makeUbuntuDistroSeries()
        old_branch = self.factory.makeAnyBranch()
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, distroseries=old_series,
            branch=old_branch)
        self.factory.makeTeam(
            name="new-team", displayname="New Team", members=[self.person])
        new_series = self.factory.makeUbuntuDistroSeries()
        with admin_logged_in():
            new_snappy_series = self.factory.makeSnappySeries(
                usable_distro_series=[new_series])
        [new_git_ref] = self.factory.makeGitRefs()
        archive = self.factory.makeArchive()

        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Edit snap package").click()
        browser.getControl("Owner").value = ["new-team"]
        browser.getControl(name="field.name").value = "new-name"
        browser.getControl(name="field.store_distro_series").value = [
            "ubuntu/%s/%s" % (new_series.name, new_snappy_series.name)]
        browser.getControl("Git", index=0).click()
        browser.getControl("Git repository").value = (
            new_git_ref.repository.identity)
        browser.getControl("Git branch").value = new_git_ref.path
        browser.getControl("Build source tarball").selected = True
        browser.getControl(
            "Automatically build when branch changes").selected = True
        browser.getControl("PPA").click()
        browser.getControl(name="field.auto_build_archive.ppa").value = (
            archive.reference)
        browser.getControl("Pocket for automatic builds").value = ["SECURITY"]
        browser.getControl("Update snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("new-name", extract_text(content.h1))
        self.assertThat("New Team", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit snap package" %
            new_series.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Source:\n%s\nEdit snap package" % new_git_ref.display_name,
            MatchesTagText(content, "source"))
        self.assertThat(
            "Source tarball:\n"
            "Builds of this snap package will also build a source tarball.\n"
            "Edit snap package",
            MatchesTagText(content, "source_tarball"))
        self.assertThat(
            "Build schedule:\n(?)\nBuilt automatically\nEdit snap package\n",
            MatchesTagText(content, "auto_build"))
        self.assertThat(
            "Source archive for automatic builds:\n%s\nEdit snap package\n" %
            archive.displayname,
            MatchesTagText(content, "auto_build_archive"))
        self.assertThat(
            "Pocket for automatic builds:\nSecurity\nEdit snap package",
            MatchesTagText(content, "auto_build_pocket"))
        self.assertThat(
            "Builds of this snap package are not automatically uploaded to "
            "the store.\nEdit snap package",
            MatchesTagText(content, "store_upload"))

    def test_edit_snap_sets_date_last_modified(self):
        # Editing a snap package sets the date_last_modified property.
        date_created = datetime(2000, 1, 1, tzinfo=pytz.UTC)
        snap = self.factory.makeSnap(
            registrant=self.person, date_created=date_created)
        with person_logged_in(self.person):
            view = SnapEditView(snap, LaunchpadTestRequest())
            view.initialize()
            view.request_action.success({
                "owner": snap.owner,
                "name": "changed",
                "distro_series": snap.distro_series,
                })
        self.assertSqlAttributeEqualsDate(snap, "date_last_modified", UTC_NOW)

    def test_edit_snap_already_exists(self):
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, name="one")
        self.factory.makeSnap(
            registrant=self.person, owner=self.person, name="two")
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Edit snap package").click()
        browser.getControl(name="field.name").value = "two"
        browser.getControl("Update snap package").click()
        self.assertEqual(
            "There is already a snap package owned by Test Person with this "
            "name.",
            extract_text(find_tags_by_class(browser.contents, "message")[1]))

    def test_edit_snap_git_url(self):
        series = self.factory.makeUbuntuDistroSeries()
        with admin_logged_in():
            snappy_series = self.factory.makeSnappySeries(
                usable_distro_series=[series])
        old_ref = self.factory.makeGitRefRemote()
        new_ref = self.factory.makeGitRefRemote()
        new_repository_url = new_ref.repository_url
        new_path = new_ref.path
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, distroseries=series,
            git_ref=old_ref, store_series=snappy_series)
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Edit snap package").click()
        browser.getControl("Git repository").value = new_repository_url
        browser.getControl("Git branch").value = new_path
        browser.getControl("Update snap package").click()
        login_person(self.person)
        content = find_main_content(browser.contents)
        self.assertThat(
            "Source:\n%s\nEdit snap package" % new_ref.display_name,
            MatchesTagText(content, "source"))

    def setUpDistroSeries(self):
        """Set up a distroseries with some available processors."""
        distroseries = self.factory.makeUbuntuDistroSeries()
        processor_names = ["386", "amd64", "hppa"]
        for name in processor_names:
            processor = getUtility(IProcessorSet).getByName(name)
            self.factory.makeDistroArchSeries(
                distroseries=distroseries, architecturetag=name,
                processor=processor)
        with admin_logged_in():
            self.factory.makeSnappySeries(usable_distro_series=[distroseries])
        return distroseries

    def assertSnapProcessors(self, snap, names):
        self.assertContentEqual(
            names, [processor.name for processor in snap.processors])

    def assertProcessorControls(self, processors_control, enabled, disabled):
        matchers = [
            MatchesStructure.byEquality(optionValue=name, disabled=False)
            for name in enabled]
        matchers.extend([
            MatchesStructure.byEquality(optionValue=name, disabled=True)
            for name in disabled])
        self.assertThat(processors_control.controls, MatchesSetwise(*matchers))

    def test_display_processors(self):
        distroseries = self.setUpDistroSeries()
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=distroseries)
        browser = self.getViewBrowser(snap, view_name="+edit", user=snap.owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(
            ["Intel 386 (386)", "AMD 64bit (amd64)", "HPPA Processor (hppa)"],
            [extract_text(option) for option in processors.displayOptions])
        self.assertContentEqual(["386", "amd64", "hppa"], processors.options)

    def test_edit_processors(self):
        distroseries = self.setUpDistroSeries()
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=distroseries)
        self.assertSnapProcessors(snap, ["386", "amd64", "hppa"])
        browser = self.getViewBrowser(snap, view_name="+edit", user=snap.owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64", "hppa"], processors.value)
        processors.value = ["386", "amd64"]
        browser.getControl("Update snap package").click()
        login_person(self.person)
        self.assertSnapProcessors(snap, ["386", "amd64"])

    def test_edit_with_invisible_processor(self):
        # It's possible for existing snap packages to have an enabled
        # processor that's no longer usable with the current distroseries,
        # which will mean it's hidden from the UI, but the non-admin
        # Snap.setProcessors isn't allowed to disable it.  Editing the
        # processor list of such a snap package leaves the invisible
        # processor intact.
        proc_386 = getUtility(IProcessorSet).getByName("386")
        proc_amd64 = getUtility(IProcessorSet).getByName("amd64")
        proc_armel = self.factory.makeProcessor(
            name="armel", restricted=True, build_by_default=False)
        distroseries = self.setUpDistroSeries()
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=distroseries)
        snap.setProcessors([proc_386, proc_amd64, proc_armel])
        browser = self.getViewBrowser(snap, view_name="+edit", user=snap.owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64"], processors.value)
        processors.value = ["amd64"]
        browser.getControl("Update snap package").click()
        login_person(self.person)
        self.assertSnapProcessors(snap, ["amd64", "armel"])

    def test_edit_processors_restricted(self):
        # A restricted processor is shown disabled in the UI and cannot be
        # enabled.
        distroseries = self.setUpDistroSeries()
        proc_armhf = self.factory.makeProcessor(
            name="armhf", restricted=True, build_by_default=False)
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="armhf",
            processor=proc_armhf)
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=distroseries)
        self.assertSnapProcessors(snap, ["386", "amd64", "hppa"])
        browser = self.getViewBrowser(snap, view_name="+edit", user=snap.owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64", "hppa"], processors.value)
        self.assertProcessorControls(
            processors, ["386", "amd64", "hppa"], ["armhf"])
        # Even if the user works around the disabled checkbox and forcibly
        # enables it, they can't enable the restricted processor.
        for control in processors.controls:
            if control.optionValue == "armhf":
                control.mech_item.disabled = False
        processors.value = ["386", "amd64", "armhf"]
        self.assertRaises(
            CannotModifySnapProcessor,
            browser.getControl("Update snap package").click)

    def test_edit_processors_restricted_already_enabled(self):
        # A restricted processor that is already enabled is shown disabled
        # in the UI.  This causes form submission to omit it, but the
        # validation code fixes that up behind the scenes so that we don't
        # get CannotModifySnapProcessor.
        proc_386 = getUtility(IProcessorSet).getByName("386")
        proc_amd64 = getUtility(IProcessorSet).getByName("amd64")
        proc_armhf = self.factory.makeProcessor(
            name="armhf", restricted=True, build_by_default=False)
        distroseries = self.setUpDistroSeries()
        self.factory.makeDistroArchSeries(
            distroseries=distroseries, architecturetag="armhf",
            processor=proc_armhf)
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=distroseries)
        snap.setProcessors([proc_386, proc_amd64, proc_armhf])
        self.assertSnapProcessors(snap, ["386", "amd64", "armhf"])
        browser = self.getUserBrowser(
            canonical_url(snap) + "/+edit", user=snap.owner)
        processors = browser.getControl(name="field.processors")
        self.assertContentEqual(["386", "amd64"], processors.value)
        self.assertProcessorControls(
            processors, ["386", "amd64", "hppa"], ["armhf"])
        processors.value = ["386"]
        browser.getControl("Update snap package").click()
        login_person(self.person)
        self.assertSnapProcessors(snap, ["386", "armhf"])

    def assertNeedStoreReauth(self, expected, initial_kwargs, data):
        initial_kwargs.setdefault("store_upload", True)
        initial_kwargs.setdefault("store_series", self.snappyseries)
        initial_kwargs.setdefault("store_name", "one")
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, **initial_kwargs)
        view = create_initialized_view(snap, "+edit", principal=self.person)
        data.setdefault("store_upload", snap.store_upload)
        data.setdefault("store_distro_series", snap.store_distro_series)
        data.setdefault("store_name", snap.store_name)
        self.assertEqual(expected, view._needStoreReauth(data))

    def test__needStoreReauth_no_change(self):
        # If the user didn't change any store settings, no reauthorization
        # is needed.
        self.assertNeedStoreReauth(False, {}, {})

    def test__needStoreReauth_different_series(self):
        # Changing the store series requires reauthorization.
        with admin_logged_in():
            new_snappyseries = self.factory.makeSnappySeries(
                usable_distro_series=[self.distroseries])
        sds = getUtility(ISnappyDistroSeriesSet).getByBothSeries(
            new_snappyseries, self.distroseries)
        self.assertNeedStoreReauth(True, {}, {"store_distro_series": sds})

    def test__needStoreReauth_different_name(self):
        # Changing the store name requires reauthorization.
        self.assertNeedStoreReauth(True, {}, {"store_name": "two"})

    def test__needStoreReauth_enable_upload(self):
        # Enabling store upload requires reauthorization.  (This can happen
        # on its own if both store_series and store_name were set to begin
        # with, which is especially plausible for Git-based snap packages,
        # or if this option is disabled and then re-enabled.  In the latter
        # case, we can't tell if store_series or store_name were also
        # changed in between, so reauthorizing is the conservative course.)
        self.assertNeedStoreReauth(
            True, {"store_upload": False}, {"store_upload": True})

    def test_edit_store_upload(self):
        # Changing store upload settings on a snap sets all the appropriate
        # fields and redirects to SSO for reauthorization.
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, store_upload=True,
            store_series=self.snappyseries, store_name="one",
            store_channels=["track/edge"])
        view_url = canonical_url(snap, view_name="+edit")
        browser = self.getNonRedirectingBrowser(url=view_url, user=self.person)
        browser.getControl("Registered store package name").value = "two"
        self.assertEqual("track", browser.getControl("Track").value)
        self.assertTrue(browser.getControl("Edge").selected)
        browser.getControl("Track").value = ""
        browser.getControl("Stable").selected = True
        root_macaroon = Macaroon()
        root_macaroon.add_third_party_caveat(
            urlsplit(config.launchpad.openid_provider_root).netloc, "",
            "dummy")
        root_macaroon_raw = root_macaroon.serialize()

        @all_requests
        def handler(url, request):
            self.request = request
            return {
                "status_code": 200,
                "content": {"macaroon": root_macaroon_raw},
                }

        self.pushConfig("snappy", store_url="http://sca.example/")
        with HTTMock(handler):
            redirection = self.assertRaises(
                HTTPError, browser.getControl("Update snap package").click)
        login_person(self.person)
        self.assertThat(snap, MatchesStructure.byEquality(
            store_name="two", store_secrets={"root": root_macaroon_raw},
            store_channels=["stable", "edge"]))
        self.assertThat(self.request, MatchesStructure.byEquality(
            url="http://sca.example/dev/api/acl/", method="POST"))
        expected_body = {
            "packages": [{"name": "two", "series": self.snappyseries.name}],
            "permissions": ["package_upload"],
            }
        self.assertEqual(expected_body, json.loads(self.request.body))
        self.assertEqual(303, redirection.code)
        parsed_location = urlsplit(redirection.hdrs["Location"])
        self.assertEqual(
            urlsplit(canonical_url(snap) + "/+authorize/+login")[:3],
            parsed_location[:3])
        expected_args = {
            "discharge_macaroon_action": ["field.actions.complete"],
            "discharge_macaroon_field": ["field.discharge_macaroon"],
            "macaroon_caveat_id": ["dummy"],
            }
        self.assertEqual(expected_args, parse_qs(parsed_location[3]))


class TestSnapAuthorizeView(BaseTestSnapView):

    def setUp(self):
        super(TestSnapAuthorizeView, self).setUp()
        self.distroseries = self.factory.makeUbuntuDistroSeries()
        with admin_logged_in():
            self.snappyseries = self.factory.makeSnappySeries(
                usable_distro_series=[self.distroseries])
        self.snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, store_upload=True,
            store_series=self.snappyseries,
            store_name=self.factory.getUniqueUnicode())

    def test_unauthorized(self):
        # A user without edit access cannot authorize snap package uploads.
        other_person = self.factory.makePerson()
        self.assertRaises(
            Unauthorized, self.getUserBrowser,
            canonical_url(self.snap) + "/+authorize", user=other_person)

    def test_begin_authorization(self):
        # With no special form actions, we return a form inviting the user
        # to begin authorization.  This allows (re-)authorizing uploads of
        # an existing snap package without having to edit it.
        snap_url = canonical_url(self.snap)
        owner = self.snap.owner
        root_macaroon = Macaroon()
        root_macaroon.add_third_party_caveat(
            urlsplit(config.launchpad.openid_provider_root).netloc, '',
            'dummy')
        root_macaroon_raw = root_macaroon.serialize()

        @all_requests
        def handler(url, request):
            self.request = request
            return {
                "status_code": 200,
                "content": {"macaroon": root_macaroon_raw},
                }

        self.pushConfig("snappy", store_url="http://sca.example/")
        with HTTMock(handler):
            browser = self.getNonRedirectingBrowser(
                url=snap_url + "/+authorize", user=self.snap.owner)
            redirection = self.assertRaises(
                HTTPError, browser.getControl("Begin authorization").click)
        self.assertThat(self.request, MatchesStructure.byEquality(
            url="http://sca.example/dev/api/acl/", method="POST"))
        with person_logged_in(owner):
            expected_body = {
                "packages": [{
                    "name": self.snap.store_name,
                    "series": self.snap.store_series.name,
                    }],
                "permissions": ["package_upload"],
                }
            self.assertEqual(expected_body, json.loads(self.request.body))
            self.assertEqual(
                {"root": root_macaroon_raw}, self.snap.store_secrets)
        self.assertEqual(303, redirection.code)
        self.assertEqual(
            snap_url + "/+authorize/+login?macaroon_caveat_id=dummy&"
            "discharge_macaroon_action=field.actions.complete&"
            "discharge_macaroon_field=field.discharge_macaroon",
            redirection.hdrs["Location"])

    def test_complete_authorization_missing_discharge_macaroon(self):
        # If the form does not include a discharge macaroon, the "complete"
        # action fails.
        with person_logged_in(self.snap.owner):
            self.snap.store_secrets = {"root": "root"}
            transaction.commit()
            form = {"field.actions.complete": "1"}
            view = create_initialized_view(
                self.snap, "+authorize", form=form, method="POST",
                principal=self.snap.owner)
            html = view()
            self.assertEqual(
                "Uploads of %s to the store were not authorized." %
                self.snap.name,
                get_feedback_messages(html)[1])
            self.assertNotIn("discharge", self.snap.store_secrets)

    def test_complete_authorization(self):
        # If the form includes a discharge macaroon, the "complete" action
        # succeeds and records the new secrets.
        with person_logged_in(self.snap.owner):
            self.snap.store_secrets = {"root": "root"}
            transaction.commit()
            form = {
                "field.actions.complete": "1",
                "field.discharge_macaroon": "discharge",
                }
            view = create_initialized_view(
                self.snap, "+authorize", form=form, method="POST",
                principal=self.snap.owner)
            self.assertEqual("", view())
            self.assertEqual(302, view.request.response.getStatus())
            self.assertEqual(
                canonical_url(self.snap),
                view.request.response.getHeader("Location"))
            self.assertEqual(
                "Uploads of %s to the store are now authorized." %
                self.snap.name,
                view.request.response.notifications[0].message)
            self.assertEqual(
                {"root": "root", "discharge": "discharge"},
                self.snap.store_secrets)


class TestSnapDeleteView(BaseTestSnapView):

    def test_unauthorized(self):
        # A user without edit access cannot delete a snap package.
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        snap_url = canonical_url(snap)
        other_person = self.factory.makePerson()
        browser = self.getViewBrowser(snap, user=other_person)
        self.assertRaises(
            LinkNotFoundError, browser.getLink, "Delete snap package")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, snap_url + "/+delete",
            user=other_person)

    def test_delete_snap_without_builds(self):
        # A snap package without builds can be deleted.
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        snap_url = canonical_url(snap)
        owner_url = canonical_url(self.person)
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Delete snap package").click()
        browser.getControl("Delete snap package").click()
        self.assertEqual(owner_url + "/+snaps", browser.url)
        self.assertRaises(NotFound, browser.open, snap_url)

    def test_delete_snap_with_builds(self):
        # A snap package with builds can be deleted.
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        build = self.factory.makeSnapBuild(snap=snap)
        self.factory.makeSnapFile(snapbuild=build)
        snap_url = canonical_url(snap)
        owner_url = canonical_url(self.person)
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Delete snap package").click()
        browser.getControl("Delete snap package").click()
        self.assertEqual(owner_url + "/+snaps", browser.url)
        self.assertRaises(NotFound, browser.open, snap_url)


class TestSnapView(BaseTestSnapView):

    def setUp(self):
        super(TestSnapView, self).setUp()
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.ubuntu, name="shiny", displayname="Shiny")
        processor = getUtility(IProcessorSet).getByName("386")
        self.distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, architecturetag="i386",
            processor=processor)
        self.factory.makeBuilder(virtualized=True)

    def makeSnap(self, **kwargs):
        if kwargs.get("branch") is None and kwargs.get("git_ref") is None:
            kwargs["branch"] = self.factory.makeAnyBranch()
        return self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name="snap-name", **kwargs)

    def makeBuild(self, snap=None, archive=None, date_created=None, **kwargs):
        if snap is None:
            snap = self.makeSnap()
        if archive is None:
            archive = self.ubuntu.main_archive
        if date_created is None:
            date_created = datetime.now(pytz.UTC) - timedelta(hours=1)
        return self.factory.makeSnapBuild(
            requester=self.person, snap=snap, archive=archive,
            distroarchseries=self.distroarchseries, date_created=date_created,
            **kwargs)

    def test_breadcrumb(self):
        snap = self.makeSnap()
        view = create_view(snap, "+index")
        # To test the breadcrumbs we need a correct traversal stack.
        view.request.traversed_objects = [self.person, snap, view]
        view.initialize()
        breadcrumbs_tag = soupmatchers.Tag(
            "breadcrumbs", "ol", attrs={"class": "breadcrumbs"})
        self.assertThat(
            view(),
            soupmatchers.HTMLContains(
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        "snap collection breadcrumb", "a",
                        text="Snap packages",
                        attrs={
                            "href": re.compile(r"/~test-person/\+snaps$"),
                            })),
                soupmatchers.Within(
                    breadcrumbs_tag,
                    soupmatchers.Tag(
                        "snap breadcrumb", "li",
                        text=re.compile(r"\ssnap-name\s")))))

    def test_index_bzr(self):
        branch = self.factory.makePersonalBranch(
            owner=self.person, name="snap-branch")
        snap = self.makeSnap(branch=branch)
        build = self.makeBuild(
            snap=snap, status=BuildStatus.FULLYBUILT,
            duration=timedelta(minutes=30))
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Snap packages snap-name
            .*
            Snap package information
            Owner: Test Person
            Distribution series: Ubuntu Shiny
            Source: lp://dev/~test-person/\\+junk/snap-branch
            Source tarball:
            Builds of this snap package will not build a source tarball.
            Build schedule: \(\?\)
            Built on request
            Source archive for automatic builds:
            Pocket for automatic builds:
            Builds of this snap package are not automatically uploaded to
            the store.
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_git(self):
        [ref] = self.factory.makeGitRefs(
            owner=self.person, target=self.person, name="snap-repository",
            paths=["refs/heads/master"])
        snap = self.makeSnap(git_ref=ref)
        build = self.makeBuild(
            snap=snap, status=BuildStatus.FULLYBUILT,
            duration=timedelta(minutes=30))
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Snap packages snap-name
            .*
            Snap package information
            Owner: Test Person
            Distribution series: Ubuntu Shiny
            Source: ~test-person/\\+git/snap-repository:master
            Source tarball:
            Builds of this snap package will not build a source tarball.
            Build schedule: \(\?\)
            Built on request
            Source archive for automatic builds:
            Pocket for automatic builds:
            Builds of this snap package are not automatically uploaded to
            the store.
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_git_url(self):
        ref = self.factory.makeGitRefRemote(
            repository_url="https://git.example.org/foo",
            path="refs/heads/master")
        snap = self.makeSnap(git_ref=ref)
        build = self.makeBuild(
            snap=snap, status=BuildStatus.FULLYBUILT,
            duration=timedelta(minutes=30))
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Snap packages snap-name
            .*
            Snap package information
            Owner: Test Person
            Distribution series: Ubuntu Shiny
            Source: https://git.example.org/foo master
            Source tarball:
            Builds of this snap package will not build a source tarball.
            Build schedule: \(\?\)
            Built on request
            Source archive for automatic builds:
            Pocket for automatic builds:
            Builds of this snap package are not automatically uploaded to
            the store.
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_success_with_buildlog(self):
        # The build log is shown if it is there.
        build = self.makeBuild(
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=30))
        build.setLog(self.factory.makeLibraryFileAlias())
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago buildlog \(.*\) i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_hides_builds_into_private_archive(self):
        # The index page hides builds into archives the user can't view.
        archive = self.factory.makeArchive(private=True)
        with person_logged_in(archive.owner):
            snap = self.makeBuild(archive=archive).snap
        self.assertIn(
            "This snap package has not been built yet.",
            self.getMainText(snap))

    def test_index_no_builds(self):
        # A message is shown when there are no builds.
        snap = self.factory.makeSnap()
        self.assertIn(
            "This snap package has not been built yet.",
            self.getMainText(snap))

    def test_index_pending(self):
        # A pending build is listed as such.
        build = self.makeBuild()
        build.queueBuild()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status When complete Architecture Archive
            Needs building in .* \(estimated\) i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_store_upload(self):
        # If the snap package is to be automatically uploaded to the store,
        # the index page shows details of this.
        with admin_logged_in():
            snappyseries = self.factory.makeSnappySeries(
                usable_distro_series=[self.distroseries])
        snap = self.makeSnap(
            store_upload=True, store_series=snappyseries,
            store_name=self.getUniqueString("store-name"))
        view = create_initialized_view(snap, "+index")
        store_upload_tag = soupmatchers.Tag(
            "store upload", "div", attrs={"id": "store_upload"})
        self.assertThat(view(), soupmatchers.HTMLContains(
            soupmatchers.Within(
                store_upload_tag,
                soupmatchers.Tag(
                    "store series name", "span", text=snappyseries.title)),
            soupmatchers.Within(
                store_upload_tag,
                soupmatchers.Tag("store name", "span", text=snap.store_name))))

    def setStatus(self, build, status):
        build.updateStatus(
            BuildStatus.BUILDING, date_started=build.date_created)
        build.updateStatus(
            status, date_finished=build.date_started + timedelta(minutes=30))

    def test_builds(self):
        # SnapView.builds produces reasonable results.
        snap = self.makeSnap()
        # Create oldest builds first so that they sort properly by id.
        date_gen = time_counter(
            datetime(2000, 1, 1, tzinfo=pytz.UTC), timedelta(days=1))
        builds = [
            self.makeBuild(snap=snap, date_created=next(date_gen))
            for i in range(11)]
        view = SnapView(snap, None)
        self.assertEqual(list(reversed(builds)), view.builds)
        self.setStatus(builds[10], BuildStatus.FULLYBUILT)
        self.setStatus(builds[9], BuildStatus.FAILEDTOBUILD)
        # When there are >= 9 pending builds, only the most recent of any
        # completed builds is returned.
        self.assertEqual(
            list(reversed(builds[:9])) + [builds[10]], view.builds)
        for build in builds[:9]:
            self.setStatus(build, BuildStatus.FULLYBUILT)
        self.assertEqual(list(reversed(builds[1:])), view.builds)

    def test_store_channels_empty(self):
        snap = self.factory.makeSnap()
        view = create_initialized_view(snap, "+index")
        self.assertEqual("", view.store_channels)

    def test_store_channels_display(self):
        snap = self.factory.makeSnap(
            store_channels=["track/stable", "track/edge"])
        view = create_initialized_view(snap, "+index")
        self.assertEqual("track/stable, track/edge", view.store_channels)


class TestSnapRequestBuildsView(BaseTestSnapView):

    def setUp(self):
        super(TestSnapRequestBuildsView, self).setUp()
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.ubuntu, name="shiny", displayname="Shiny")
        self.architectures = []
        for processor, architecture in ("386", "i386"), ("amd64", "amd64"):
            das = self.factory.makeDistroArchSeries(
                distroseries=self.distroseries, architecturetag=architecture,
                processor=getUtility(IProcessorSet).getByName(processor))
            das.addOrUpdateChroot(self.factory.makeLibraryFileAlias())
            self.architectures.append(das)
        self.snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name="snap-name")

    def test_request_builds_page(self):
        # The +request-builds page is sane.
        self.assertTextMatchesExpressionIgnoreWhitespace("""
            Request builds for snap-name
            Snap packages
            snap-name
            Request builds
            Source archive:
            Primary Archive for Ubuntu Linux
            PPA
            \(Find&hellip;\)
            Architectures:
            amd64
            i386
            Pocket:
            Release
            Security
            Updates
            Proposed
            Backports
            \(\?\)
            The package stream within the source distribution series to use
            when building the snap package.
            or
            Cancel
            """,
            self.getMainText(self.snap, "+request-builds", user=self.person))

    def test_request_builds_not_owner(self):
        # A user without launchpad.Edit cannot request builds.
        self.assertRaises(
            Unauthorized, self.getViewBrowser, self.snap, "+request-builds")

    def test_request_builds_action(self):
        # Requesting a build creates pending builds.
        browser = self.getViewBrowser(
            self.snap, "+request-builds", user=self.person)
        self.assertTrue(browser.getControl("amd64").selected)
        self.assertTrue(browser.getControl("i386").selected)
        browser.getControl("Request builds").click()

        login_person(self.person)
        builds = self.snap.pending_builds
        self.assertContentEqual(
            [self.ubuntu.main_archive], set(build.archive for build in builds))
        self.assertContentEqual(
            ["amd64", "i386"],
            [build.distro_arch_series.architecturetag for build in builds])
        self.assertContentEqual(
            [PackagePublishingPocket.UPDATES],
            set(build.pocket for build in builds))
        self.assertContentEqual(
            [2510], set(build.buildqueue_record.lastscore for build in builds))

    def test_request_builds_ppa(self):
        # Selecting a different archive creates builds in that archive.
        ppa = self.factory.makeArchive(
            distribution=self.ubuntu, owner=self.person, name="snap-ppa")
        browser = self.getViewBrowser(
            self.snap, "+request-builds", user=self.person)
        browser.getControl("PPA").click()
        browser.getControl(name="field.archive.ppa").value = ppa.reference
        self.assertTrue(browser.getControl("amd64").selected)
        browser.getControl("i386").selected = False
        browser.getControl("Request builds").click()

        login_person(self.person)
        builds = self.snap.pending_builds
        self.assertEqual([ppa], [build.archive for build in builds])

    def test_request_builds_no_architectures(self):
        # Selecting no architectures causes a validation failure.
        browser = self.getViewBrowser(
            self.snap, "+request-builds", user=self.person)
        browser.getControl("amd64").selected = False
        browser.getControl("i386").selected = False
        browser.getControl("Request builds").click()
        self.assertIn(
            "You need to select at least one architecture.",
            extract_text(find_main_content(browser.contents)))

    def test_request_builds_rejects_duplicate(self):
        # A duplicate build request causes a notification.
        self.snap.requestBuild(
            self.person, self.ubuntu.main_archive, self.distroseries["amd64"],
            PackagePublishingPocket.UPDATES)
        browser = self.getViewBrowser(
            self.snap, "+request-builds", user=self.person)
        self.assertTrue(browser.getControl("amd64").selected)
        self.assertTrue(browser.getControl("i386").selected)
        browser.getControl("Request builds").click()
        main_text = extract_text(find_main_content(browser.contents))
        self.assertIn("1 new build has been queued.", main_text)
        self.assertIn(
            "An identical build is already pending for amd64.", main_text)
