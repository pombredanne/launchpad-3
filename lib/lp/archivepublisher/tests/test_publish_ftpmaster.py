# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publish-ftpmaster cron script."""

__metaclass__ = type

from apt_pkg import TagFile
import logging
import os
from textwrap import dedent
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.config import getPubConfig
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.services.log.logger import (
    BufferLogger,
    DevNullLogger,
    )
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.archivepublisher.scripts.publish_ftpmaster import (
    compose_env_string,
    compose_shell_boolean,
    find_run_parts_dir,
    get_working_dists,
    PublishFTPMaster,
    shell_quote,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCase,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


def path_exists(*path_components):
    """Does the given file or directory exist?"""
    return file_exists(os.path.join(*path_components))


def name_spph_suite(spph):
    """Return name of `spph`'s suite."""
    return spph.distroseries.name + pocketsuffix[spph.pocket]


def get_pub_config(distro):
    """Find the publishing config for `distro`."""
    return getUtility(IPublisherConfigSet).getByDistribution(distro)


def get_archive_root(pub_config):
    """Return the archive root for the given publishing config."""
    return os.path.join(pub_config.root_dir, pub_config.distribution.name)


def get_dists_root(pub_config):
    """Return the dists root directory for the given publishing config."""
    return os.path.join(get_archive_root(pub_config), "dists")


def get_distscopy_root(pub_config):
    """Return the "distscopy" root for the given publishing config."""
    return get_archive_root(pub_config) + "-distscopy"


def get_run_parts_path():
    """Get relative path to run-parts location the Launchpad source."""
    return os.path.join("cronscripts", "publishing", "distro-parts")


def write_marker_file(path, contents):
    """Write a marker file for checking directory movements.

    :param path: A list of path components.
    :param contents: Text to write into the file.
    """
    marker = file(os.path.join(*path), "w")
    marker.write(contents)
    marker.flush()
    marker.close()


def read_marker_file(path):
    """Read the contents of a marker file.

    :param return: Contents of the marker file.
    """
    return file(os.path.join(*path)).read()


class HelpersMixin:
    """Helpers for the PublishFTPMaster tests."""

    def enableRunParts(self, parts_directory=None):
        """Set up for run-parts execution.

        :param parts_directory: Base location for the run-parts
            directories.  If omitted, the run-parts directory from the
            Launchpad source tree will be used.
        """
        if parts_directory is None:
            parts_directory = get_run_parts_path()

        config.push("run-parts", dedent("""\
            [archivepublisher]
            run_parts_location: %s
            """ % parts_directory))

        self.addCleanup(config.pop, "run-parts")


class TestPublishFTPMasterHelpers(TestCase):

    def test_compose_env_string_iterates_env_dict(self):
        env = {
            "A": "1",
            "B": "2",
        }
        env_string = compose_env_string(env)
        self.assertIn(env_string, ["A=1 B=2", "B=2 A=1"])

    def test_compose_env_string_combines_env_dicts(self):
        env1 = {"A": "1"}
        env2 = {"B": "2"}
        env_string = compose_env_string(env1, env2)
        self.assertIn(env_string, ["A=1 B=2", "B=2 A=1"])

    def test_compose_env_string_overrides_repeated_keys(self):
        self.assertEqual("A=2", compose_env_string({"A": "1"}, {"A": "2"}))

    def test_shell_quote_quotes_string(self):
        self.assertEqual('"x"', shell_quote("x"))

    def test_shell_quote_escapes_string(self):
        self.assertEqual('"\\\\"', shell_quote("\\"))

    def test_shell_quote_does_not_escape_its_own_escapes(self):
        self.assertEqual('"\\$"', shell_quote("$"))

    def test_shell_quote_escapes_entire_string(self):
        self.assertEqual('"\\$\\$\\$"', shell_quote("$$$"))

    def test_compose_shell_boolean_shows_True_as_yes(self):
        self.assertEqual("yes", compose_shell_boolean(True))

    def test_compose_shell_boolean_shows_False_as_no(self):
        self.assertEqual("no", compose_shell_boolean(False))


class TestFindRunPartsDir(TestCaseWithFactory, HelpersMixin):
    layer = ZopelessDatabaseLayer

    def test_find_run_parts_dir_finds_relative_runparts_directory(self):
        self.enableRunParts()
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertEqual(
            os.path.join(
                config.root, get_run_parts_path(), "ubuntu", "finalize.d"),
            find_run_parts_dir(ubuntu, "finalize.d"))

    def test_find_run_parts_dir_finds_absolute_runparts_directory(self):
        self.enableRunParts(os.path.join(config.root, get_run_parts_path()))
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertEqual(
            os.path.join(
                config.root, get_run_parts_path(), "ubuntu", "finalize.d"),
                find_run_parts_dir(ubuntu, "finalize.d"))

    def test_find_run_parts_dir_ignores_blank_config(self):
        self.enableRunParts("")
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertIs(None, find_run_parts_dir(ubuntu, "finalize.d"))

    def test_find_run_parts_dir_ignores_none_config(self):
        self.enableRunParts("none")
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.assertIs(None, find_run_parts_dir(ubuntu, "finalize.d"))

    def test_find_run_parts_dir_ignores_nonexistent_directory(self):
        self.enableRunParts()
        distro = self.factory.makeDistribution()
        self.assertIs(None, find_run_parts_dir(distro, "finalize.d"))


class TestPublishFTPMasterScript(TestCaseWithFactory, HelpersMixin):
    layer = LaunchpadZopelessLayer

    # Location of shell script.
    SCRIPT_PATH = "cronscripts/publish-ftpmaster.py"

    def setUpForScriptRun(self, distro):
        """Mock up config to run the script on `distro`."""
        pub_config = getUtility(IPublisherConfigSet).getByDistribution(distro)
        pub_config.root_dir = unicode(
            self.makeTemporaryDirectory())

    def makeDistro(self):
        """Create a `Distribution` for testing.

        The distribution will have a publishing directory set up, which
        will be cleaned up after the test.
        """
        return self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))

    def prepareUbuntu(self):
        """Obtain a reference to Ubuntu, set up for testing.

        A temporary publishing directory will be set up, and it will be
        cleaned up after the test.
        """
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.setUpForScriptRun(ubuntu)
        return ubuntu

    def makeScript(self, distro=None, extra_args=[]):
        """Produce instance of the `PublishFTPMaster` script."""
        if distro is None:
            distro = self.makeDistro()
        script = PublishFTPMaster(test_args=["-d", distro.name] + extra_args)
        script.txn = self.layer.txn
        script.logger = DevNullLogger()
        return script

    def readReleaseFile(self, filename):
        """Read a Release file, return as a keyword/value dict."""
        sections = list(TagFile(file(filename)))
        self.assertEqual(1, len(sections))
        return dict(sections[0])

    def enableCommercialCompat(self):
        """Enable commercial-compat.sh runs for the duration of the test."""
        config.push("commercial-compat", dedent("""\
            [archivepublisher]
            run_commercial_compat: true
            """))
        self.addCleanup(config.pop, "commercial-compat")

    def installRunPartsScript(self, distro, parts_dir, script_code):
        """Set up a run-parts script, and configure it to run.

        :param distro: The `Distribution` you're testing on.  Must have
            a temporary directory as its publishing root directory.
        :param parts_dir: The run-parts subdirectory to execute:
            publish-distro.d or finalize.d.
        :param script_code: The code to go into the script.
        """
        distro_config = get_pub_config(distro)
        parts_base = os.path.join(distro_config.root_dir, "distro-parts")
        self.enableRunParts(parts_base)
        script_dir = os.path.join(parts_base, distro.name, parts_dir)
        os.makedirs(script_dir)
        script_path = os.path.join(script_dir, self.factory.getUniqueString())
        script_file = file(script_path, "w")
        script_file.write(script_code)
        script_file.close()
        os.chmod(script_path, 0755)

    def test_script_runs_successfully(self):
        ubuntu = self.prepareUbuntu()
        self.layer.txn.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_script_is_happy_with_no_publications(self):
        distro = self.makeDistro()
        self.makeScript(distro).main()

    def test_produces_listings(self):
        distro = self.makeDistro()
        self.makeScript(distro).main()
        self.assertTrue(
            path_exists(get_archive_root(get_pub_config(distro)), 'ls-lR.gz'))

    def test_can_run_twice(self):
        test_publisher = SoyuzTestPublisher()
        distroseries = test_publisher.setUpDefaultDistroSeries()
        distro = distroseries.distribution
        pub_config = get_pub_config(distro)
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        test_publisher.getPubSource()

        self.setUpForScriptRun(distro)
        self.makeScript(distro).main()
        self.makeScript(distro).main()

    def test_publishes_package(self):
        test_publisher = SoyuzTestPublisher()
        distroseries = test_publisher.setUpDefaultDistroSeries()
        distro = distroseries.distribution
        pub_config = get_pub_config(distro)
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        test_publisher.getPubSource()

        self.setUpForScriptRun(distro)
        self.makeScript(distro).main()

        archive_root = get_archive_root(pub_config)
        dists_root = get_dists_root(pub_config)

        dsc = os.path.join(
            archive_root, 'pool', 'main', 'f', 'foo', 'foo_666.dsc')
        self.assertEqual("I do not care about sources.", file(dsc).read())
        overrides = os.path.join(
            archive_root + '-overrides', distroseries.name + '_main_source')
        self.assertEqual(dsc, file(overrides).read().rstrip())
        self.assertTrue(path_exists(
            dists_root, distroseries.name, 'main', 'source', 'Sources.gz'))
        self.assertTrue(path_exists(
            dists_root, distroseries.name, 'main', 'source', 'Sources.bz2'))

        distcopyseries = os.path.join(dists_root, distroseries.name)
        release = self.readReleaseFile(
            os.path.join(distcopyseries, "Release"))
        self.assertEqual(distro.displayname, release['Origin'])
        self.assertEqual(distro.displayname, release['Label'])
        self.assertEqual(distroseries.name, release['Suite'])
        self.assertEqual(distroseries.name, release['Codename'])
        self.assertEqual("main", release['Components'])
        self.assertEqual("", release["Architectures"])
        self.assertIn("Date", release)
        self.assertIn("Description", release)
        self.assertNotEqual("", release["MD5Sum"])
        self.assertNotEqual("", release["SHA1"])
        self.assertNotEqual("", release["SHA256"])

        main_release = self.readReleaseFile(
            os.path.join(distcopyseries, 'main', 'source', "Release"))
        self.assertEqual(distroseries.name, main_release["Archive"])
        self.assertEqual("main", main_release["Component"])
        self.assertEqual(distro.displayname, main_release["Origin"])
        self.assertEqual(distro.displayname, main_release["Label"])
        self.assertEqual("source", main_release["Architecture"])

    def test_getDirtySuites_returns_suite_with_pending_publication(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertEqual([name_spph_suite(spph)], script.getDirtySuites())

    def test_getDirtySuites_returns_suites_with_pending_publications(self):
        distro = self.makeDistro()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=self.factory.makeDistroSeries(
                    distribution=distro))
            for counter in xrange(2)]

        script = self.makeScript(distro)
        script.setUp()
        self.assertContentEqual(
            [name_spph_suite(spph) for spph in spphs],
            script.getDirtySuites())

    def test_getDirtySuites_ignores_suites_without_pending_publications(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertEqual([], script.getDirtySuites())

    def test_getDirtySecuritySuites_returns_security_suites(self):
        distro = self.makeDistro()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=self.factory.makeDistroSeries(
                    distribution=distro),
                pocket=PackagePublishingPocket.SECURITY)
            for counter in xrange(2)]

        script = self.makeScript(distro)
        script.setUp()
        self.assertContentEqual(
            [name_spph_suite(spph) for spph in spphs],
            script.getDirtySecuritySuites())

    def test_getDirtySecuritySuites_ignores_non_security_suites(self):
        distroseries = self.factory.makeDistroSeries()
        spphs = [
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries, pocket=pocket)
            for pocket in [
                PackagePublishingPocket.RELEASE,
                PackagePublishingPocket.UPDATES,
                PackagePublishingPocket.PROPOSED,
                PackagePublishingPocket.BACKPORTS,
                ]]
        script = self.makeScript(distroseries.distribution)
        script.setUp()
        self.assertEqual([], script.getDirtySecuritySuites())

    def test_rsync_copies_files(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        dists_root = get_dists_root(get_pub_config(distro))
        dists_backup = os.path.join(
            get_distscopy_root(get_pub_config(distro)), "dists")
        os.makedirs(dists_backup)
        os.makedirs(dists_root)
        write_marker_file([dists_root, "new-file"], "New file")
        script.rsyncBackupDists()
        self.assertEqual(
            "New file", read_marker_file([dists_backup, "new-file"]))

    def test_rsync_cleans_up_obsolete_files(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        dists_backup = os.path.join(
            get_distscopy_root(get_pub_config(distro)), "dists")
        os.makedirs(dists_backup)
        old_file = [dists_backup, "old-file"]
        write_marker_file(old_file, "old-file")
        os.makedirs(get_dists_root(get_pub_config(distro)))
        script.rsyncBackupDists()
        self.assertFalse(path_exists(*old_file))

    def test_setUpDirs_creates_directory_structure(self):
        distro = self.makeDistro()
        pub_config = get_pub_config(distro)
        archive_root = get_archive_root(pub_config)
        dists_root = get_dists_root(pub_config)
        script = self.makeScript(distro)
        script.setUp()

        self.assertFalse(file_exists(archive_root))

        script.setUpDirs()

        self.assertTrue(file_exists(archive_root))
        self.assertTrue(file_exists(dists_root))
        self.assertTrue(file_exists(get_distscopy_root(pub_config)))

    def test_setUpDirs_does_not_mind_if_dist_directories_already_exist(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.setUpDirs()
        self.assertTrue(file_exists(get_archive_root(get_pub_config(distro))))

    def test_publishDistroArchive_runs_parts(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.runParts = FakeMethod()
        script.publishDistroArchive(distro.main_archive)
        self.assertEqual(1, script.runParts.call_count)
        args, kwargs = script.runParts.calls[0]
        parts_dir, env = args
        self.assertEqual("publish-distro.d", parts_dir)

    def test_runPublishDistroParts_passes_parameters(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.runParts = FakeMethod()
        script.runPublishDistroParts(distro.main_archive)
        args, kwargs = script.runParts.calls[0]
        parts_dir, env = args
        required_parameters = set([
            "ARCHIVEROOT", "DISTSROOT", "OVERRIDEROOT"])
        missing_parameters = required_parameters.difference(set(env.keys()))
        self.assertEqual(set(), missing_parameters)

    def test_runCommercialCompat_runs_commercial_compat_script(self):
        # XXX JeroenVermeulen 2011-03-29 bug=741683: Retire
        # runCommercialCompat as soon as Dapper support ends.
        self.enableCommercialCompat()
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        script.executeShell = FakeMethod()
        script.runCommercialCompat()
        self.assertEqual(1, script.executeShell.call_count)
        args, kwargs = script.executeShell.calls[0]
        command_line, = args
        self.assertIn("commercial-compat.sh", command_line)

    def test_runCommercialCompat_runs_only_for_ubuntu(self):
        # XXX JeroenVermeulen 2011-03-29 bug=741683: Retire
        # runCommercialCompat as soon as Dapper support ends.
        self.enableCommercialCompat()
        script = self.makeScript(self.makeDistro())
        script.setUp()
        script.executeShell = FakeMethod()
        script.runCommercialCompat()
        self.assertEqual(0, script.executeShell.call_count)

    def test_runCommercialCompat_runs_only_if_configured(self):
        # XXX JeroenVermeulen 2011-03-29 bug=741683: Retire
        # runCommercialCompat as soon as Dapper support ends.
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        script.executeShell = FakeMethod()
        script.runCommercialCompat()
        self.assertEqual(0, script.executeShell.call_count)

    def test_generateListings_writes_ls_lR_gz(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.generateListings()
        pass

    def test_clearEmptyDirs_cleans_up_empty_directories(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        empty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'empty-dir')
        os.makedirs(empty_dir)
        script.clearEmptyDirs()
        self.assertFalse(file_exists(empty_dir))

    def test_clearEmptyDirs_does_not_clean_up_nonempty_directories(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        nonempty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'nonempty-dir')
        os.makedirs(nonempty_dir)
        write_marker_file([nonempty_dir, "placeholder"], "Data here!")
        script.clearEmptyDirs()
        self.assertTrue(file_exists(nonempty_dir))

    def test_processOptions_finds_distribution(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.processOptions()
        self.assertEqual(distro.name, script.options.distribution)
        self.assertEqual(distro, script.distribution)

    def test_processOptions_complains_about_unknown_distribution(self):
        script = self.makeScript()
        script.options.distribution = self.factory.getUniqueString()
        self.assertRaises(LaunchpadScriptFailure, script.processOptions)

    def test_runParts_runs_parts(self):
        self.enableRunParts()
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        script.executeShell = FakeMethod()
        script.runParts("finalize.d", {})
        self.assertEqual(1, script.executeShell.call_count)
        args, kwargs = script.executeShell.calls[-1]
        command_line, = args
        self.assertIn("run-parts", command_line)
        self.assertIn(
            "cronscripts/publishing/distro-parts/ubuntu/finalize.d",
            command_line)

    def test_runParts_passes_parameters(self):
        self.enableRunParts()
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        script.executeShell = FakeMethod()
        key = self.factory.getUniqueString()
        value = self.factory.getUniqueString()
        script.runParts("finalize.d", {key: value})
        args, kwargs = script.executeShell.calls[-1]
        command_line, = args
        self.assertIn("%s=%s" % (key, value), command_line)

    def test_executeShell_executes_shell_command(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        marker = os.path.join(
            get_pub_config(distro).root_dir, "marker")
        script.executeShell("touch %s" % marker)
        self.assertTrue(file_exists(marker))

    def test_executeShell_reports_failure_if_requested(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)

        class ArbitraryFailure(Exception):
            """Some exception that's not likely to come from elsewhere."""

        self.assertRaises(
            ArbitraryFailure,
            script.executeShell, "/bin/false", failure=ArbitraryFailure())

    def test_executeShell_does_not_report_failure_if_not_requested(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        # The test is that this does not fail:
        script.executeShell("/bin/false")

    def test_runFinalizeParts_passes_parameters(self):
        script = self.makeScript(self.prepareUbuntu())
        script.setUp()
        script.runParts = FakeMethod()
        script.runFinalizeParts()
        args, kwargs = script.runParts.calls[0]
        parts_dir, env = args
        required_parameters = set(["ARCHIVEROOTS", "SECURITY_UPLOAD_ONLY"])
        missing_parameters = required_parameters.difference(set(env.keys()))
        self.assertEqual(set(), missing_parameters)

    def test_publishSecurityUploads_skips_pub_if_no_security_updates(self):
        script = self.makeScript()
        script.setUp()
        script.setUpDirs()
        script.installDists = FakeMethod()
        script.publishSecurityUploads()
        self.assertEqual(0, script.installDists.call_count)

    def test_publishAllUploads_publishes_all_distro_archives(self):
        distro = self.makeDistro()
        distroseries = self.factory.makeDistroSeries(distribution=distro)
        partner_archive = self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        for archive in distro.all_distro_archives:
            self.factory.makeSourcePackagePublishingHistory(
                distroseries=distroseries,
                archive=archive)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.publishDistroArchive = FakeMethod()
        script.publishAllUploads()
        published_archives = [
            args[0] for args, kwargs in script.publishDistroArchive.calls]

        self.assertContentEqual(
            distro.all_distro_archives, published_archives)
        self.assertIn(distro.main_archive, published_archives)
        self.assertIn(partner_archive, published_archives)

    def test_recoverWorkingDists_is_quiet_normally(self):
        script = self.makeScript()
        script.setUp()
        script.logger = BufferLogger()
        script.logger.setLevel(logging.INFO)
        script.recoverWorkingDists()
        self.assertEqual('', script.logger.getLogBuffer())

    def test_recoverWorkingDists_recovers_working_directory(self):
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.logger = BufferLogger()
        script.logger.setLevel(logging.INFO)
        script.setUpDirs()
        archive_config = script.configs[ArchivePurpose.PRIMARY]
        backup_dists = os.path.join(
            archive_config.archiveroot + "-distscopy", "dists")
        working_dists = get_working_dists(archive_config)
        os.rename(backup_dists, working_dists)
        write_marker_file([working_dists, "marker"], "Recovered")
        script.recoverWorkingDists()
        self.assertEqual(
            "Recovered", read_marker_file([backup_dists, "marker"]))
        self.assertNotEqual('', script.logger.getLogBuffer())

    def test_publishes_first_security_updates_then_all_updates(self):
        script = self.makeScript()
        script.publish = FakeMethod()
        script.main()
        self.assertEqual(2, script.publish.call_count)
        args, kwargs = script.publish.calls[0]
        self.assertEqual({'security_only': True}, kwargs)
        args, kwargs = script.publish.calls[1]
        self.assertEqual(False, kwargs.get('security_only', False))

    def test_security_run_publishes_only_security_updates(self):
        script = self.makeScript(extra_args=['--security-only'])
        script.publish = FakeMethod()
        script.main()
        self.assertEqual(1, script.publish.call_count)
        args, kwargs = script.publish.calls[0]
        self.assertEqual({'security_only': True}, kwargs)

    def test_publishAllUploads_processes_all_archives(self):
        distro = self.makeDistro()
        partner_archive = self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro)
        script.publishDistroArchive = FakeMethod()
        script.setUp()
        script.publishAllUploads()
        published_archives = [
            args[0] for args, kwargs in script.publishDistroArchive.calls]
        self.assertContentEqual(
            [distro.main_archive, partner_archive], published_archives)

    def test_runFinalizeParts_quotes_archiveroots(self):
        # Passing ARCHIVEROOTS to the finalize.d scripts is a bit
        # difficult because the variable holds multiple values in a
        # single, double-quoted string.  Escaping and quoting a sequence
        # of escaped and quoted items won't work.
        # This test establishes how a script can sanely deal with the
        # list.  It'll probably go wrong if the configured archive root
        # contains spaces and such, but should work with Unix-sensible
        # paths.
        distro = self.makeDistro()
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()

        # Create a run-parts script that creates marker files in each of
        # the archive roots, and writes an expected string to them.
        # Doesn't write to a marker file that already exists, because it
        # might be a sign that the path it received is ridiculously
        # wrong.  Don't want to go overwriting random files now do we?
        self.installRunPartsScript(distro, "finalize.d", dedent("""\
            #!/bin/sh -e
            MARKER_NAME="marker file"
            for DIRECTORY in $ARCHIVEROOTS
            do
                MARKER="$DIRECTORY/$MARKER_NAME"
                if [ -e "$MARKER" ]
                then
                    echo "Marker file $MARKER already exists." >&2
                    exit 1
                fi
                echo "This is an archive root." >"$MARKER"
            done
            """))

        script.runFinalizeParts()

        for archive in [distro.main_archive, distro.getArchive("partner")]:
            archive_root = getPubConfig(archive).archiveroot
            self.assertEqual(
                "This is an archive root.",
                self.readMarkerFile([archive_root, "marker file"]).rstrip(),
                "Did not find expected marker for %s."
                % archive.purpose.title)
