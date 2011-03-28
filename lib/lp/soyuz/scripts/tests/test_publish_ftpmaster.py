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
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.scripts.publish_ftpmaster import PublishFTPMaster
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    )
from lp.testing.fakemethod import FakeMethod


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

    def test_script_runs_successfully(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.setUpForScriptRun(ubuntu)
        transaction.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_produces_listings(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        rootdir = self.setUpForScriptRun(ubuntu)
        transaction.commit()
        self.makeScript(ubuntu).main()

        listing = os.path.join(rootdir, 'ubuntu', 'ls-lR.gz')
        self.assertTrue(os.access(listing, os.F_OK))

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
        transaction.commit()
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
        self.assertTrue(os.access(sources, os.F_OK))
        sources = os.path.join(
            rootdir, distro.name, 'dists', distroseries.name, 'main',
            'source', 'Sources.bz2')
        self.assertTrue(os.access(sources, os.F_OK))

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
        distscopyroot = archive_root + "-distscopy"
        os.makedirs(distscopyroot)

        script = self.makeScript(distro)
        script.processAccepted = FakeMethod(failure=ValueError("Boom"))
        try:
            script.main()
        except ValueError:
            pass

        self.assertTrue(
            os.access(os.path.join(distscopyroot, "dists"), os.F_OK))

    def test_cleanup_moves_dists_to_old_if_published(self):
        pass

    def test_getDirtySuites_returns_suites_with_pending_publications(self):
        pass

    def test_gatherSecuritySuites_returns_security_suites(self):
        pass

    def test_rsync_copies_files(self):
        pass

    def test_rsync_cleans_up_obsolete_files(self):
        pass

    def test_setUpDirs_XXX(self):
        pass
    def test_setUpDirs_XXX(self):
        pass
    def test_setUpDirs_XXX(self):
        pass

    def test_publishDistroArchive_runs_publish_distro(self):
        pass

    def test_publishDistroArchive_runs_parts(self):
        pass

    def test_runPublishDistroParts_passes_parameters(self):
        pass

    def test_installDists_XXX(self):
        pass
    def test_installDists_XXX(self):
        pass
    def test_installDists_XXX(self):
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
