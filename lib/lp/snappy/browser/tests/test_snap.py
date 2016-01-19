# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test snap package views."""

__metaclass__ = type

from datetime import (
    datetime,
    timedelta,
    )
import re
from textwrap import dedent

from fixtures import FakeLogger
from mechanize import LinkNotFoundError
import pytz
import soupmatchers
from testtools.matchers import (
    MatchesSetwise,
    MatchesStructure,
    )
from zope.component import getUtility
from zope.publisher.interfaces import NotFound
from zope.security.interfaces import Unauthorized

from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.processor import IProcessorSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.interfaces.series import SeriesStatus
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
    SNAP_FEATURE_FLAG,
    SnapFeatureDisabled,
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
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))

    def test_canonical_url(self):
        owner = self.factory.makePerson(name="person")
        snap = self.factory.makeSnap(
            registrant=owner, owner=owner, name=u"snap")
        self.assertEqual(
            "http://launchpad.dev/~person/+snap/snap", canonical_url(snap))

    def test_snap(self):
        snap = self.factory.makeSnap()
        obj, _, _ = test_traverse(
            "http://launchpad.dev/~%s/+snap/%s" % (snap.owner.name, snap.name))
        self.assertEqual(snap, obj)


class TestSnapViewsFeatureFlag(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_feature_flag_disabled(self):
        # Without a feature flag, we will not create new Snaps.
        branch = self.factory.makeAnyBranch()
        self.assertRaises(
            SnapFeatureDisabled, create_initialized_view, branch, "+new-snap")


class TestSnapAddView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapAddView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
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
        branch = self.factory.makeAnyBranch()
        with person_logged_in(self.person):
            view = create_initialized_view(branch, "+new-snap")
        self.assertEqual(development, view.initial_values["distro_series"])

    def test_create_new_snap_not_logged_in(self):
        branch = self.factory.makeAnyBranch()
        self.assertRaises(
            Unauthorized, self.getViewBrowser, branch, view_name="+new-snap",
            no_login=True)

    def test_create_new_snap_bzr(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.DEVELOPMENT)
        branch = self.factory.makeAnyBranch()
        source_display = branch.display_name
        browser = self.getViewBrowser(
            branch, view_name="+new-snap", user=self.person)
        browser.getControl("Name").value = "snap-name"
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("snap-name", extract_text(content.h1))
        self.assertThat(
            "Test Person", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit snap package" %
            distroseries.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Source:\n%s\nEdit snap package" % source_display,
            MatchesTagText(content, "source"))

    def test_create_new_snap_git(self):
        archive = self.factory.makeArchive()
        distroseries = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.DEVELOPMENT)
        [git_ref] = self.factory.makeGitRefs()
        source_display = git_ref.display_name
        browser = self.getViewBrowser(
            git_ref, view_name="+new-snap", user=self.person)
        browser.getControl("Name").value = "snap-name"
        browser.getControl("Create snap package").click()

        content = find_main_content(browser.contents)
        self.assertEqual("snap-name", extract_text(content.h1))
        self.assertThat(
            "Test Person", MatchesPickerText(content, "edit-owner"))
        self.assertThat(
            "Distribution series:\n%s\nEdit snap package" %
            distroseries.fullseriesname,
            MatchesTagText(content, "distro_series"))
        self.assertThat(
            "Source:\n%s\nEdit snap package" % source_display,
            MatchesTagText(content, "source"))

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


class TestSnapAdminView(BrowserTestCase):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSnapAdminView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.useFixture(FakeLogger())
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

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
        # Admins can change require_virtualized.
        login("admin@canonical.com")
        ppa_admin = self.factory.makePerson(
            member_of=[getUtility(ILaunchpadCelebrities).ppa_admin])
        login_person(self.person)
        snap = self.factory.makeSnap(registrant=self.person)
        self.assertTrue(snap.require_virtualized)
        browser = self.getViewBrowser(snap, user=ppa_admin)
        browser.getLink("Administer snap package").click()
        browser.getControl("Require virtualized builders").selected = False
        browser.getControl("Update snap package").click()
        login_person(self.person)
        self.assertFalse(snap.require_virtualized)

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


class TestSnapEditView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapEditView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.useFixture(FakeLogger())
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_edit_snap(self):
        archive = self.factory.makeArchive()
        old_series = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.CURRENT)
        old_branch = self.factory.makeAnyBranch()
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, distroseries=old_series,
            branch=old_branch)
        self.factory.makeTeam(
            name="new-team", displayname="New Team", members=[self.person])
        new_series = self.factory.makeDistroSeries(
            distribution=archive.distribution, status=SeriesStatus.DEVELOPMENT)
        [new_git_ref] = self.factory.makeGitRefs()

        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Edit snap package").click()
        browser.getControl("Owner").value = ["new-team"]
        browser.getControl("Name").value = "new-name"
        browser.getControl(name="field.distro_series").value = [
            str(new_series.id)]
        browser.getControl("Git", index=0).click()
        browser.getControl("Git repository").value = (
            new_git_ref.repository.identity)
        browser.getControl("Git branch").value = new_git_ref.path
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
                "name": u"changed",
                "distro_series": snap.distro_series,
                })
        self.assertSqlAttributeEqualsDate(snap, "date_last_modified", UTC_NOW)

    def test_edit_snap_already_exists(self):
        snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person, name=u"one")
        self.factory.makeSnap(
            registrant=self.person, owner=self.person, name=u"two")
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Edit snap package").click()
        browser.getControl("Name").value = "two"
        browser.getControl("Update snap package").click()
        self.assertEqual(
            "There is already a snap package owned by Test Person with this "
            "name.",
            extract_text(find_tags_by_class(browser.contents, "message")[1]))

    def setUpDistroSeries(self):
        """Set up a distroseries with some available processors."""
        distroseries = self.factory.makeUbuntuDistroSeries()
        processor_names = ["386", "amd64", "hppa"]
        for name in processor_names:
            processor = getUtility(IProcessorSet).getByName(name)
            self.factory.makeDistroArchSeries(
                distroseries=distroseries, architecturetag=name,
                processor=processor)
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
        self.useFixture(FakeLogger())
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


class TestSnapDeleteView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapDeleteView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.person = self.factory.makePerson(
            name="test-person", displayname="Test Person")

    def test_unauthorized(self):
        # A user without edit access cannot delete a snap package.
        self.useFixture(FakeLogger())
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
        self.useFixture(FakeLogger())
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        snap_url = canonical_url(snap)
        owner_url = canonical_url(self.person)
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Delete snap package").click()
        browser.getControl("Delete snap package").click()
        self.assertEqual(owner_url, browser.url)
        self.assertRaises(NotFound, browser.open, snap_url)

    def test_delete_snap_with_builds(self):
        # A snap package with builds cannot be deleted.
        snap = self.factory.makeSnap(registrant=self.person, owner=self.person)
        self.factory.makeSnapBuild(snap=snap)
        browser = self.getViewBrowser(snap, user=self.person)
        browser.getLink("Delete snap package").click()
        self.assertIn("This snap package cannot be deleted", browser.contents)
        self.assertRaises(
            LookupError, browser.getControl, "Delete snap package")


class TestSnapView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
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

    def makeSnap(self, branch=None, git_ref=None):
        if branch is None and git_ref is None:
            branch = self.factory.makeAnyBranch()
        return self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name=u"snap-name", branch=branch,
            git_ref=git_ref)

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
            Latest builds
            Status When complete Architecture Archive
            Successfully built 30 minutes ago i386
            Primary Archive for Ubuntu Linux
            """, self.getMainText(build.snap))

    def test_index_git(self):
        [ref] = self.factory.makeGitRefs(
            owner=self.person, target=self.person, name=u"snap-repository",
            paths=[u"refs/heads/master"])
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


class TestSnapRequestBuildsView(BrowserTestCase):

    layer = LaunchpadFunctionalLayer

    def setUp(self):
        super(TestSnapRequestBuildsView, self).setUp()
        self.useFixture(FeatureFixture({SNAP_FEATURE_FLAG: u"on"}))
        self.useFixture(FakeLogger())
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
        self.person = self.factory.makePerson()
        self.snap = self.factory.makeSnap(
            registrant=self.person, owner=self.person,
            distroseries=self.distroseries, name=u"snap-name")

    def test_request_builds_page(self):
        # The +request-builds page is sane.
        pattern = dedent("""\
            Request builds for snap-name
            Snap packages
            snap-name
            Request builds
            Source archive:
            Primary Archive for Ubuntu Linux
            PPA
            (Find&hellip;)
            Architectures:
            amd64
            i386
            Pocket:
            Release
            Security
            Updates
            Proposed
            Backports
            or
            Cancel""")
        main_text = self.getMainText(
            self.snap, "+request-builds", user=self.person)
        self.assertEqual(pattern, main_text)

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
            [PackagePublishingPocket.RELEASE],
            set(build.pocket for build in builds))
        self.assertContentEqual(
            [2505], set(build.buildqueue_record.lastscore for build in builds))

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
            PackagePublishingPocket.RELEASE)
        browser = self.getViewBrowser(
            self.snap, "+request-builds", user=self.person)
        self.assertTrue(browser.getControl("amd64").selected)
        self.assertTrue(browser.getControl("i386").selected)
        browser.getControl("Request builds").click()
        main_text = extract_text(find_main_content(browser.contents))
        self.assertIn("1 new build has been queued.", main_text)
        self.assertIn(
            "An identical build is already pending for amd64.", main_text)
