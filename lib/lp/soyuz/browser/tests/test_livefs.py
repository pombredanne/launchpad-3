# Copyright 2014-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test live filesystem views."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import json

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
import pytz
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.registry.interfaces.series import SeriesStatus
from lp.services.database.constants import UTC_NOW
from lp.services.features.testing import FeatureFixture
from lp.services.webapp import canonical_url
from lp.services.webapp.servers import LaunchpadTestRequest
from lp.soyuz.browser.livefs import (
    LiveFSAdminView,
    LiveFSEditView,
    LiveFSView,
    )
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LiveFSFeatureDisabled,
    )
from lp.testing import (
    BrowserTestCase,
    login,
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    time_counter,
    )
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
    find_tags_by_class,
    get_feedback_messages,
    )
from lp.testing.publication import test_traverse
from lp.testing.views import create_initialized_view


class TestLiveFSNavigation(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSNavigation, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        distribution = self.factory.makeDistribution(
            name="distro", owner=owner)
        distroseries = self.factory.makeDistroSeries(
            distribution=distribution, name="unstable")
        livefs = self.factory.makeLiveFS(
            registrant=owner, owner=owner, distroseries=distroseries,
            name="livefs")
        self.assertEqual(
            "http://launchpad.dev/~person/+livefs/distro/unstable/livefs",
            canonical_url(livefs))

    def test_livefs(self):
        livefs = self.factory.makeLiveFS()
        obj, _, _ = test_traverse(
            "http://launchpad.dev/~%s/+livefs/%s/%s/%s" % (
                livefs.owner.name, livefs.distro_series.distribution.name,
                livefs.distro_series.name, livefs.name))
        self.assertEqual(livefs, obj)


class TestLiveFSViewsFeatureFlag(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new LiveFSes.
        person = self.factory.makePerson()
        self.assertRaises(
            LiveFSFeatureDisabled, create_initialized_view,
            person, "+new-livefs")


class TestLiveFSAddView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSAddView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.useFixture(FakeLogger())
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_initial_distroseries(self):
        # The initial distroseries is the newest that is current or in
        # development.
        archive = self.factory.makeArchive(owner=self.person)
        self.factory.makeDistroSeries(
            distribution=archive.distribution, version="14.04",
            status=SeriesStatus.DEVELOPMENT)
        development = self.factory.makeDistroSeries(
            distribution=archive.distribution, version="14.10",
            status=SeriesStatus.DEVELOPMENT)
        self.factory.makeDistroSeries(
            distribution=archive.distribution, version="15.04",
            status=SeriesStatus.EXPERIMENTAL)
        with person_logged_in(self.person):
            view = create_initialized_view(self.person, "+new-livefs")
        self.assertEqual(development, view.initial_values["distro_series"])

    def test_create_new_livefs_not_logged_in(self):
        self.assertRaises(
            Unauthorized, self.getViewBrowser, self.person,
            view_name="+new-livefs", no_login=True)

    def test_create_new_livefs(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.DEVELOPMENT)
        browser = self.getViewBrowser(
            self.person, view_name="+new-livefs", user=self.person)
        browser.getControl("Name").value = "ubuntu-core"
        browser.getControl("Live filesystem build metadata").value = (
            '{"product": "ubuntu-core", "image_format": "plain"}')
        browser.getControl("Create live filesystem").click()

        content = find_main_content(browser.contents)
        self.assertEqual("ubuntu-core\nEdit", extract_text(content.h1))
        self.assertThat(
            "Test Person", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit live filesystem" %
            distroseries.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Metadata:\nimage_format\nplain\nproduct\nubuntu-core",
            MatchesTagText(content, "metadata"))

    def test_create_new_livefs_users_teams_as_owner_options(self):
        # Teams that the user is in are options for the live filesystem owner.
        self.factory.makeTeam(
            name="test-team", displayname="Test Team", members=[self.person])
        browser = self.getViewBrowser(
            self.person, view_name="+new-livefs", user=self.person)
        options = browser.getControl("Owner").displayOptions
        self.assertEqual(
            ["Test Person (test-person)", "Test Team (test-team)"],
            sorted(str(option) for option in options))

    def test_create_new_livefs_invalid_metadata(self):
        # The metadata field must contain valid JSON.
        browser = self.getViewBrowser(
            self.person, view_name="+new-livefs", user=self.person)
        browser.getControl("Name").value = "ubuntu-core"
        browser.getControl("Live filesystem build metadata").value = "{"
        browser.getControl("Create live filesystem").click()
        json_error = str(self.assertRaises(ValueError, json.loads, "{"))
        self.assertEqual(
            json_error, get_feedback_messages(browser.contents)[1])


class TestLiveFSAdminView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSAdminView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.useFixture(FakeLogger())
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_unauthorized(self):
        # A non-admin user cannot administer a live filesystem.
        login_person(self.person)
        livefs = self.factory.makeLiveFS(registrant=self.person)
        livefs_url = canonical_url(livefs)
        browser = self.getViewBrowser(livefs, user=self.person)
        self.assertRaises(
            LinkNotFoundError, browser.getLink, "Administer live filesystem")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, livefs_url + "/+admin",
            user=self.person)

    def test_admin_livefs(self):
        # Admins can change require_virtualized.
        login("admin@canonical.com")
        ppa_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).ppa_admin])
        login_person(self.person)
        livefs = self.factory.makeLiveFS(registrant=self.person)
        self.assertTrue(livefs.require_virtualized)
        browser = self.getViewBrowser(livefs, user=ppa_admin)
        browser.getLink("Administer live filesystem").click()
        browser.getControl("Require virtualized builders").selected = False
        browser.getControl("Update live filesystem").click()
        login_person(self.person)
        self.assertFalse(livefs.require_virtualized)

    def test_admin_livefs_sets_date_last_modified(self):
        # Administering a live filesystem sets the date_last_modified property.
        login("admin@canonical.com")
        ppa_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).ppa_admin])
        login_person(self.person)
        date_created = datetime(2000, 1, 1, tzinfo=pytz.UTC)
        livefs = self.factory.makeLiveFS(
            registrant=self.person, date_created=date_created)
        login_person(ppa_admin)
        view = LiveFSAdminView(livefs, LaunchpadTestRequest())
        view.initialize()
        view.request_action.success({"require_virtualized": False})
        self.assertSqlAttributeEqualsDate(
            livefs, "date_last_modified", UTC_NOW)


class TestLiveFSEditView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLiveFSEditView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.useFixture(FakeLogger())
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_edit_livefs(self):
        archive = self.factory.makeArchive()
        old_series = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.CURRENT)
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person, distroseries=old_series)
        self.factory.makeTeam(
            name="new-team", displayname="New Team", members=[self.person])
        new_series = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.DEVELOPMENT)

        browser = self.getViewBrowser(livefs, user=self.person)
        browser.getLink("Edit live filesystem").click()
        browser.getControl("Owner").value = ["new-team"]
        browser.getControl("Name").value = "new-name"
        browser.getControl(name="field.distro_series").value = [
            str(new_series.id)]
        browser.getControl("Live filesystem build metadata").value = (
            '{"product": "new-name"}')
        browser.getControl("Update live filesystem").click()

        content = find_main_content(browser.contents)
        self.assertEqual("new-name\nEdit", extract_text(content.h1))
        self.assertThat("New Team", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit live filesystem" %
            new_series.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Metadata:\nproduct\nnew-name",
            MatchesTagText(content, "metadata"))

    def test_edit_livefs_sets_date_last_modified(self):
        # Editing a live filesystem sets the date_last_modified property.
        date_created = datetime(2000, 1, 1, tzinfo=pytz.UTC)
        livefs = self.factory.makeLiveFS(
            registrant=self.person, date_created=date_created)
        with person_logged_in(self.person):
            view = LiveFSEditView(livefs, LaunchpadTestRequest())
            view.initialize()
            view.request_action.success({
                "owner": livefs.owner,
                "name": "changed",
                "distro_series": livefs.distro_series,
                "metadata": "{}",
                })
        self.assertSqlAttributeEqualsDate(
            livefs, "date_last_modified", UTC_NOW)

    def test_edit_livefs_already_exists(self):
        distroseries = self.factory.makeDistroSeries(
            distribution=getUtility(ILaunchpadCelebrities).ubuntu,
            displayname="Grumpy")
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person,
            distroseries=distroseries, name="one")
        self.factory.makeLiveFS(
            registrant=self.person, owner=self.person,
            distroseries=distroseries, name="two")
        browser = self.getViewBrowser(livefs, user=self.person)
        browser.getLink("Edit live filesystem").click()
        browser.getControl("Name").value = "two"
        browser.getControl("Update live filesystem").click()
        self.assertEqual(
            "There is already a live filesystem for Grumpy owned by "
            "Test Person with this name.",
            extract_text(find_tags_by_class(browser.contents, "message")[1]))


class TestLiveFSDeleteView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestLiveFSDeleteView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_unauthorized(self):
        # A user without edit access cannot delete a live filesystem.
        self.useFixture(FakeLogger())
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person)
        livefs_url = canonical_url(livefs)
        other_person = self.factory.makePerson()
        browser = self.getViewBrowser(livefs, user=other_person)
        self.assertRaises(
            LinkNotFoundError, browser.getLink, "Delete live filesystem")
        self.assertRaises(
            Unauthorized, self.getUserBrowser, livefs_url + "/+delete",
            user=other_person)

    def test_delete_livefs_without_builds(self):
        # A live filesystem without builds can be deleted.
        self.useFixture(FakeLogger())
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person)
        livefs_url = canonical_url(livefs)
        owner_url = canonical_url(self.person)
        browser = self.getViewBrowser(livefs, user=self.person)
        browser.getLink("Delete live filesystem").click()
        browser.getControl("Delete live filesystem").click()
        self.assertEqual(owner_url, browser.url)
        self.assertRaises(NotFound, browser.open, livefs_url)

    def test_delete_livefs_with_builds(self):
        # A live filesystem without builds cannot be deleted.
        livefs = self.factory.makeLiveFS(
            registrant=self.person, owner=self.person)
        self.factory.makeLiveFSBuild(livefs=livefs)
        browser = self.getViewBrowser(livefs, user=self.person)
        browser.getLink("Delete live filesystem").click()
        self.assertIn(
            "This live filesystem cannot be deleted", browser.contents)
        self.assertRaises(
            LookupError, browser.getControl, "Delete live filesystem")


class TestLiveFSView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestLiveFSView, self).setUp()
        self.useFixture(FeatureFixture({LIVEFS_FEATURE_FLAG: "on"}))
        self.ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.distroseries = self.factory.makeDistroSeries(
            distribution=self.ubuntu, name="shiny", displayname="Shiny")
        processor = getUtility(IProcessorSet).getByName("386")
        self.distroarchseries = self.factory.makeDistroArchSeries(
            distroseries=self.distroseries, architecturetag="i386",
            processor=processor)
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")
        self.factory.makeBuilder(virtualized=True)

    def makeLiveFS(self):
        return self.factory.makeLiveFS(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name="livefs-name",
            metadata={"project": "ubuntu-test"})

    def makeBuild(self, livefs=None, archive=None, date_created=None,
                  **kwargs):
        if livefs is None:
            livefs = self.makeLiveFS()
        if archive is None:
            archive = self.ubuntu.main_archive
        if date_created is None:
            date_created = datetime.now(pytz.UTC) - timedelta(hours=1)
        return self.factory.makeLiveFSBuild(
            requester=self.person, livefs=livefs, archive=archive,
            distroarchseries=self.distroarchseries, date_created=date_created,
            **kwargs)

    def test_index(self):
        build = self.makeBuild(
            status=BuildStatus.FULLYBUILT, duration=timedelta(minutes=30))
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Live filesystems livefs-name
            .*
            Live filesystem information
            Owner: Test Person
            Distribution series: Ubuntu Shiny
            Metadata: project ubuntu-test
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.livefs))

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
            """, self.getMainText(build.livefs))

    def test_index_hides_builds_into_private_archive(self):
        # The index page hides builds into archives the user can't view.
        archive = self.factory.makeArchive(private=True)
        with person_logged_in(archive.owner):
            livefs = self.makeBuild(archive=archive).livefs
        self.assertIn(
            "This live filesystem has not been built yet.",
            self.getMainText(livefs))

    def test_index_no_builds(self):
        # A message is shown when there are no builds.
        livefs = self.factory.makeLiveFS()
        self.assertIn(
            "This live filesystem has not been built yet.",
            self.getMainText(livefs))

    def test_index_pending(self):
        # A pending build is listed as such.
        build = self.makeBuild()
        build.queueBuild()
        self.assertTextMatchesExpressionIgnoreWhitespace("""\
            Latest builds
            Status When complete Architecture Archive
            Needs building in .* \(estimated\) i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.livefs))

    def setStatus(self, build, status):
        build.updateStatus(
            BuildStatus.BUILDING, date_started=build.date_created)
        build.updateStatus(
            status, date_finished=build.date_started + timedelta(minutes=30))

    def test_builds(self):
        # LiveFSView.builds produces reasonable results.
        livefs = self.makeLiveFS()
        # Create oldest builds first so that they sort properly by id.
        date_gen = time_counter(
            datetime(2000, 1, 1, tzinfo=pytz.UTC), timedelta(days=1))
        builds = [
            self.makeBuild(livefs=livefs, date_created=next(date_gen))
            for i in range(11)]
        view = LiveFSView(livefs, None)
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
