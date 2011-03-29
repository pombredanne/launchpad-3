# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publish-ftpmaster cron script."""

__metaclass__ = type

import os
from textwrap import dedent
import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.services.log.logger import DevNullLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.scripts.publish_ftpmaster import (
    compose_env_string,
    compose_shell_boolean,
    find_run_parts_dir,
    PublishFTPMaster,
    )
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
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


class TestPublishFTPMasterHelpers(TestCaseWithFactory, HelpersMixin):
    layer = ZopelessDatabaseLayer

    def test_compose_env_string_iterates_env(self):
        env = {
            "A": "1",
            "B": "2",
        }
        env_string = compose_env_string(env)
        self.assertIn(env_string, ["A=1 B=2", "B=2 A=1"])

    def test_compose_shell_boolean_shows_True_as_yes(self):
        self.assertEqual("yes", compose_shell_boolean(True))

    def test_compose_shell_boolean_shows_False_as_no(self):
        self.assertEqual("no", compose_shell_boolean(False))

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

    def getDistro(self, use_ubuntu=False):
        """Obtain a `Distribution` for testing, and set up test directory.

        :param use_ubuntu: Use Ubuntu as the test distro?  If not,
            create a new one.
        """
        if use_ubuntu:
            distro = getUtility(ILaunchpadCelebrities).ubuntu
        else:
            distro = self.factory.makeDistribution()
        self.setUpForScriptRun(distro)
        return distro

    def makeScript(self, distro=None):
        """Produce instance of the `PublishFTPMaster` script."""
        if distro is None:
            distro = self.getDistro()
        script = PublishFTPMaster(test_args=["-d", distro.name])
        script.txn = transaction
        script.logger = DevNullLogger()
        return script

    def readReleaseFile(self, filename):
        """Read a Release file, return as a keyword/value dict."""
        lines = []
        for line in file(filename):
            if line.startswith(' '):
                lines[-1] += line
            else:
                lines.append(line)
        return dict(
            (key, value.strip())
            for key, value in [line.split(':', 1) for line in lines])

    def writeMarkerFile(self, path, contents):
        """Write a marker file for checking direction movements.

        :param path: A list of path components.
        :param contents: Text to write into the file.
        """
        marker = file(os.path.join(*path), "w")
        marker.write(contents)
        marker.flush()
        marker.close()

    def readMarkerFile(self, path):
        """Read the contents of a marker file.

        :param return: Contents of the marker file.
        """
        return file(os.path.join(*path)).read()

    def enableCommercialCompat(self):
        """Enable commercial-compat.sh runs for the duration of the test."""
        config.push("commercial-compat", dedent("""\
            [archivepublisher]
            run_commercial_compat: true
            """))
        self.addCleanup(config.pop, "commercial-compat")

    def test_script_runs_successfully(self):
        ubuntu = self.getDistro(use_ubuntu=True)
        transaction.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_script_is_happy_with_no_publications(self):
        distro = self.getDistro()
        self.makeScript(distro).main()

    def test_produces_listings(self):
        distro = self.getDistro()
        self.makeScript(distro).main()
        self.assertTrue(
            path_exists(get_archive_root(get_pub_config(distro)), 'ls-lR.gz'))

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

    def test_cleanup_moves_dists_to_new_if_not_published(self):
        distro = self.getDistro()
        pub_config = get_pub_config(distro)
        dists_root = get_dists_root(pub_config)
        dists_copy_root = get_distscopy_root(pub_config)
        new_distsroot = dists_root + ".new"
        os.makedirs(new_distsroot)
        self.writeMarkerFile([new_distsroot, "marker"], "dists.new")
        os.makedirs(dists_copy_root)

        script = self.makeScript(distro)
        script.setUp()
        script.cleanUp()
        self.assertEqual(
            "dists.new",
            self.readMarkerFile([dists_copy_root, "dists", "marker"]))

    def test_cleanup_moves_dists_to_old_if_published(self):
        distro = self.getDistro()
        pub_config = get_pub_config(distro)
        dists_root = get_dists_root(pub_config)
        old_distsroot = dists_root + ".old"
        dists_copy_root = get_distscopy_root(pub_config)
        os.makedirs(old_distsroot)
        self.writeMarkerFile([old_distsroot, "marker"], "dists.old")
        os.makedirs(dists_copy_root)

        script = self.makeScript(distro)
        script.setUp()
        script.done_pub = True
        script.cleanUp()
        self.assertEqual(
            "dists.old",
            self.readMarkerFile([dists_copy_root, "dists", "marker"]))

    def test_getDirtySuites_returns_suite_with_pending_publication(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertEqual([name_spph_suite(spph)], script.getDirtySuites())

    def test_getDirtySuites_returns_suites_with_pending_publications(self):
        distro = self.getDistro()
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
        distro = self.getDistro()
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
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        dists_root = get_dists_root(get_pub_config(distro))
        os.makedirs(dists_root)
        os.makedirs(dists_root + ".new")
        self.writeMarkerFile([dists_root, "new-file"], "New file")
        script.rsyncNewDists(ArchivePurpose.PRIMARY)
        self.assertEqual(
            "New file",
            self.readMarkerFile([dists_root + ".new", "new-file"]))

    def test_rsync_cleans_up_obsolete_files(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        dists_root = get_dists_root(get_pub_config(distro))
        os.makedirs(dists_root)
        os.makedirs(dists_root + ".new")
        old_file = [dists_root + ".new", "old-file"]
        self.writeMarkerFile(old_file, "old-file")
        script.rsyncNewDists(ArchivePurpose.PRIMARY)
        self.assertFalse(path_exists(*old_file))

    def test_setUpDirs_creates_directory_structure(self):
        distro = self.getDistro()
        pub_config = get_pub_config(distro)
        archive_root = get_archive_root(pub_config)
        dists_root = get_dists_root(pub_config)
        script = self.makeScript(distro)
        script.setUp()

        self.assertFalse(file_exists(archive_root))

        script.setUpDirs()

        self.assertTrue(file_exists(archive_root))
        self.assertTrue(file_exists(dists_root))
        self.assertTrue(file_exists(dists_root + ".new"))

    def test_setUpDirs_does_not_mind_if_directories_already_exist(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.setUpDirs()
        self.assertTrue(file_exists(get_archive_root(get_pub_config(distro))))

    def test_setUpDirs_moves_dists_to_dists_new(self):
        distro = self.getDistro()
        dists_root = get_dists_root(get_pub_config(distro))
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        self.writeMarkerFile([dists_root, "marker"], "X")
        script.setUpDirs()
        self.assertEqual(
            "X", self.readMarkerFile([dists_root + ".new", "marker"]))

    def test_publishDistroArchive_runs_parts(self):
        distro = self.getDistro()
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
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.runParts = FakeMethod()
        script.runPublishDistroParts(distro.main_archive)
        args, kwargs = script.runParts.calls[0]
        parts_dir, env = args
        required_parameters = set(["DISTSROOT", "ARCHIVEROOT"])
        missing_parameters = set(env.keys()).difference(required_parameters)
        self.assertEqual(set(), missing_parameters)

    def test_installDists_sets_done_pub(self):
        script = self.makeScript()
        script.setUp()
        script.setUpDirs()
        self.assertFalse(script.done_pub)
        script.installDists()
        self.assertTrue(script.done_pub)

    def test_installDists_replaces_distsroot(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        pub_config = get_pub_config(distro)
        dists_root = get_dists_root(pub_config)

        self.writeMarkerFile([dists_root, "marker"], "old")
        self.writeMarkerFile([dists_root + ".new", "marker"], "new")

        script.installDists()

        self.assertEqual("new", self.readMarkerFile([dists_root, "marker"]))
        self.assertEqual( "old", self.readMarkerFile(
            [get_distscopy_root(pub_config), "dists", "marker"]))

    def test_runCommercialCompat_runs_commercial_compat_script(self):
        # XXX JeroenVermeulen 2011-03-29 bug=741683: Retire
        # runCommercialCompat as soon as Dapper support ends.
        self.enableCommercialCompat()
        script = self.makeScript(self.getDistro(use_ubuntu=True))
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
        script = self.makeScript(self.getDistro(use_ubuntu=False))
        script.setUp()
        script.executeShell = FakeMethod()
        script.runCommercialCompat()
        self.assertEqual(0, script.executeShell.call_count)

    def test_runCommercialCompat_runs_only_if_configured(self):
        # XXX JeroenVermeulen 2011-03-29 bug=741683: Retire
        # runCommercialCompat as soon as Dapper support ends.
        script = self.makeScript(self.getDistro(use_ubuntu=True))
        script.setUp()
        script.executeShell = FakeMethod()
        script.runCommercialCompat()
        self.assertEqual(0, script.executeShell.call_count)

    def test_generateListings_writes_ls_lR_gz(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.generateListings()
        pass

    def test_clearEmptyDirs_cleans_up_empty_directories(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        empty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'empty-dir')
        os.makedirs(empty_dir)
        script.clearEmptyDirs()
        self.assertFalse(file_exists(empty_dir))

    def test_clearEmptyDirs_does_not_clean_up_nonempty_directories(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        nonempty_dir = os.path.join(
            get_dists_root(get_pub_config(distro)), 'nonempty-dir')
        os.makedirs(nonempty_dir)
        self.writeMarkerFile([nonempty_dir, "placeholder"], "Data here!")
        script.clearEmptyDirs()
        self.assertTrue(file_exists(nonempty_dir))

    def test_processOptions_finds_distribution(self):
        distro = self.getDistro()
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
        script = self.makeScript(self.getDistro(use_ubuntu=True))
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
        script = self.makeScript(self.getDistro(use_ubuntu=True))
        script.setUp()
        script.executeShell = FakeMethod()
        key = self.factory.getUniqueString()
        value = self.factory.getUniqueString()
        script.runParts("finalize.d", {key: value})
        args, kwargs = script.executeShell.calls[-1]
        command_line, = args
        self.assertIn("%s=%s" % (key, value), command_line)

    def test_executeShell_executes_shell_command(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        marker = os.path.join(
            get_pub_config(distro).root_dir, "marker")
        script.executeShell("touch %s" % marker)
        self.assertTrue(file_exists(marker))

    def test_executeShell_reports_failure_if_requested(self):
        distro = self.getDistro()
        script = self.makeScript(distro)

        class ArbitraryFailure(Exception):
            """Some exception that's not likely to come from elsewhere."""

        self.assertRaises(
            ArbitraryFailure,
            script.executeShell, "/bin/false", failure=ArbitraryFailure())

    def test_executeShell_does_not_report_failure_if_not_requested(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        # The test is that this does not fail:
        script.executeShell("/bin/false")

    def test_runFinalizeParts_passes_parameters(self):
        script = self.makeScript(self.getDistro(use_ubuntu=True))
        script.setUp()
        script.runParts = FakeMethod()
        script.runFinalizeParts()
        args, kwargs = script.runParts.calls[0]
        parts_dir, env = args
        required_parameters = set([
            "ARCHIVEROOTS",
            "PRIMARY_ARCHIVEROOT",
            "SECURITY_UPLOAD_ONLY",
            ])
        missing_parameters = set(env.keys()).difference(required_parameters)
        self.assertEqual(set(), missing_parameters)

    def test_publishSecurityUploads_skips_pub_if_no_security_updates(self):
        script = self.makeScript(self.getDistro())
        script.setUp()
        script.setUpDirs()
        script.installDists = FakeMethod()
        script.publishSecurityUploads()
        self.assertEqual(0, script.installDists.call_count)

    def test_publishSecurityUploads_runs_finalize_parts(self):
        distro = self.getDistro()
        self.factory.makeSourcePackagePublishingHistory(
            distroseries=self.factory.makeDistroSeries(distribution=distro),
            pocket=PackagePublishingPocket.SECURITY)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.runFinalizeParts = FakeMethod()
        script.publishSecurityUploads()
        self.assertEqual(1, script.runFinalizeParts.call_count)
        args, kwargs = script.runFinalizeParts.calls[0]
        self.assertTrue(kwargs["security_only"])

    def test_publishAllUploads_publishes_all_distro_archives(self):
        distro = self.getDistro()
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

    def test_publishAllUploads_runs_finalize_parts(self):
        distro = self.getDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.runFinalizeParts = FakeMethod()
        script.publishAllUploads()
        self.assertEqual(1, script.runFinalizeParts.call_count)
