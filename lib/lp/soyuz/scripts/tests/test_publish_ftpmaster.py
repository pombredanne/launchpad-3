# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publish-ftpmaster cron script."""

__metaclass__ = type

import os
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.pocket import (
    PackagePublishingPocket,
    pocketsuffix,
    )
from lp.services.log.logger import DevNullLogger
from lp.services.utils import file_exists
from lp.soyuz.enums import (
    ArchivePurpose,
    PackagePublishingStatus,
    )
from lp.soyuz.scripts.publish_ftpmaster import PublishFTPMaster
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


def name_spph_suite(spph):
    """Return name of `spph`'s suite."""
    return spph.distroseries.name + pocketsuffix[spph.pocket]


class TestPublishFTPMaster(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer

    # Location of shell script.
    SCRIPT_PATH = "cronscripts/publish-ftpmaster.py"

    def setUpForScriptRun(self, distro):
        """Prepare for a run of `PublishFTPMaster` for the named distro."""
        config = getUtility(IPublisherConfigSet).getByDistribution(distro)
        config.root_dir = unicode(self.makeTemporaryDirectory())
        return config.root_dir

    def makeScript(self, distro):
        """Produce instance of the `PublishFTPMaster` script."""
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

    def test_script_runs_successfully(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.setUpForScriptRun(ubuntu)
        transaction.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_script_is_happy_with_no_publications(self):
        distro = self.factory.makeDistribution()
        self.setUpForScriptRun(distro)
        self.makeScript(distro).main()

    def test_produces_listings(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        rootdir = self.setUpForScriptRun(ubuntu)
        self.makeScript(ubuntu).main()

        listing = os.path.join(rootdir, 'ubuntu', 'ls-lR.gz')
        self.assertTrue(file_exists(listing))

    def test_publishes_package(self):
        test_publisher = SoyuzTestPublisher()
        distroseries = test_publisher.setUpDefaultDistroSeries()
        distro = distroseries.distribution
        self.factory.makeComponentSelection(
            distroseries=distroseries, component="main")
        self.factory.makeArchive(
            distribution=distro, purpose=ArchivePurpose.PARTNER)
        test_publisher.getPubSource()

        rootdir = self.setUpForScriptRun(distro)
        self.makeScript(distro).main()

        dsc = os.path.join(
            rootdir, distro.name, 'pool', 'main', 'f', 'foo', 'foo_666.dsc')
        self.assertEqual("I do not care about sources.", file(dsc).read())
        overrides = os.path.join(
            rootdir, distro.name + '-overrides',
            distroseries.name + '_main_source')
        self.assertEqual(dsc, file(overrides).read().rstrip())
        sources = os.path.join(
            rootdir, distro.name, 'dists', distroseries.name, 'main',
            'source', 'Sources.gz')
        self.assertTrue(file_exists(sources))
        sources = os.path.join(
            rootdir, distro.name, 'dists', distroseries.name, 'main',
            'source', 'Sources.bz2')
        self.assertTrue(file_exists(sources))

        distcopyseries = os.path.join(
            rootdir, distro.name, 'dists', distroseries.name)
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
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)

        archive_root = os.path.join(root_dir, distro.name)
        new_distsroot = os.path.join(archive_root, "dists.new")
        os.makedirs(new_distsroot)
        self.writeMarkerFile([new_distsroot, "marker"], "dists.new")
        distscopyroot = archive_root + "-distscopy"
        os.makedirs(distscopyroot)

        script = self.makeScript(distro)
        script.setUp()
        script.cleanUp()
        self.assertEqual(
            "dists.new",
            self.readMarkerFile([distscopyroot, "dists", "marker"]))

    def test_cleanup_moves_dists_to_old_if_published(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        archive_root = os.path.join(root_dir, distro.name)
        old_distsroot = os.path.join(archive_root, "dists.old")
        os.makedirs(old_distsroot)
        self.writeMarkerFile([old_distsroot, "marker"], "dists.old")
        distscopyroot = archive_root + "-distscopy"
        os.makedirs(distscopyroot)

        script = self.makeScript(distro)
        script.setUp()
        script.done_pub = True
        script.cleanUp()
        self.assertEqual(
            "dists.old",
            self.readMarkerFile([distscopyroot, "dists", "marker"]))

    def test_getDirtySuites_returns_suite_with_pending_publication(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        script = self.makeScript(spph.distroseries.distribution)
        script.setUp()
        self.assertEqual([name_spph_suite(spph)], script.getDirtySuites())

    def test_getDirtySuites_returns_suites_with_pending_publications(self):
        distro = self.factory.makeDistribution()
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

    def test_gatherSecuritySuites_returns_security_suites(self):
        distro = self.factory.makeDistribution()
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
            script.gatherSecuritySuites())

    def test_gatherSecuritySuites_ignores_non_security_suites(self):
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
        self.assertEqual([], script.gatherSecuritySuites())

    def test_rsync_copies_files(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        script = self.makeScript(distro)
        script.setUp()
        dists_root = os.path.join(root_dir, distro.name, "dists")
        os.makedirs(dists_root)
        os.makedirs(dists_root + ".new")
        self.writeMarkerFile([dists_root, "new-file"], "New file")
        script.rsyncNewDists(ArchivePurpose.PRIMARY)
        self.assertEqual(
            "New file",
            self.readMarkerFile([dists_root + ".new", "new-file"]))

    def test_rsync_cleans_up_obsolete_files(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        script = self.makeScript(distro)
        script.setUp()
        dists_root = os.path.join(root_dir, distro.name, "dists")
        os.makedirs(dists_root)
        os.makedirs(dists_root + ".new")
        old_file = os.path.join(dists_root + ".new", "old-file")
        self.writeMarkerFile([old_file], "old-file")
        script.rsyncNewDists(ArchivePurpose.PRIMARY)
        self.assertFalse(file_exists(old_file))

    def test_setUpDirs_creates_directory_structure(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        archive_root = os.path.join(root_dir, distro.name)
        script = self.makeScript(distro)
        script.setUp()

        self.assertFalse(file_exists(archive_root))

        script.setUpDirs()

        self.assertTrue(file_exists(archive_root))
        self.assertTrue(file_exists(os.path.join(archive_root, "dists")))
        self.assertTrue(file_exists(os.path.join(archive_root, "dists.new")))

    def test_setUpDirs_does_not_mind_if_directories_already_exist(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        archive_root = os.path.join(root_dir, distro.name)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        script.setUpDirs()
        self.assertTrue(file_exists(archive_root))

    def test_setUpDirs_moves_dists_to_dists_new(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        archive_root = os.path.join(root_dir, distro.name)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        self.writeMarkerFile([archive_root, "dists", "marker"], "X")
        script.setUpDirs()
        self.assertEqual(
            "X", self.readMarkerFile([archive_root, "dists.new", "marker"]))

    def test_publishDistroArchive_runs_parts(self):
        distro = self.factory.makeDistribution()
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
        distro = self.factory.makeDistribution()
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
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        self.assertFalse(script.done_pub)
        script.installDists()
        self.assertTrue(script.done_pub)

    def test_installDists_replaces_distsroot(self):
        distro = self.factory.makeDistribution()
        root_dir = self.setUpForScriptRun(distro)
        script = self.makeScript(distro)
        script.setUp()
        script.setUpDirs()
        archive_root = os.path.join(root_dir, distro.name)
        distsroot = os.path.join(archive_root, "dists")

        self.writeMarkerFile([distsroot, "marker"], "old")
        self.writeMarkerFile([distsroot + ".new", "marker"], "new")

        script.installDists()

        self.assertEqual("new", self.readMarkerFile([distsroot, "marker"]))
        self.assertEqual( "old", self.readMarkerFile(
            [archive_root + "-distscopy", "dists", "marker"]))

    def test_installDists_replaces_distscopyroot(self):
        pass

    def test_runCommercialCompat_runs_commercial_compat_script(self):
        pass

    def test_runCommercialCompat_runs_only_for_ubuntu(self):
        pass

    def test_runCommercialCompat_runs_only_on_production_config(self):
        pass

    def test_generateListings_writes_ls_lR_gz(self):
        pass

    def test_clearEmptyDirs_cleans_up_empty_directories(self):
        pass

    def test_clearEmptyDirs_does_not_clean_up_nonempty_directories(self):
        pass

    def test_processOptions_finds_distribution(self):
        pass

    def test_processOptions_complains_about_unknown_distribution(self):
        pass

    def test_runParts_runs_parts(self):
        pass

    def test_runFinalizeParts_passes_parameters(self):
        pass

    def test_publishSecurityUploads_XXX(self):
        pass
    def test_publishSecurityUploads_XXX(self):
        pass
    def test_publishSecurityUploads_XXX(self):
        pass

    def test_publishAllUploads_publishes_all_distro_archives(self):
        pass

    def test_publishAllUploads_XXX(self):
        pass
    def test_publishAllUploads_XXX(self):
        pass
    def test_publishAllUploads_XXX(self):
        pass
