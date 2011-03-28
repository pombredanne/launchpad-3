# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publish-ftpmaster cron script."""

__metaclass__ = type

import os
import re
import transaction
from zope.component import getUtility

from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.log.logger import DevNullLogger
from lp.soyuz.enums import ArchivePurpose
from lp.soyuz.scripts.publish_ftpmaster import PublishFTPMaster
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import (
    run_script,
    TestCaseWithFactory,
    )


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
            line = line.rstrip()
            if line.startswith(' '):
                lines[-1] += line
            else:
                lines.append(line)
        return dict(
            line.split(': ', 1)
            for line in lines if re.match("[^:]+: [^\s]+", line))

    def test_script_runs_successfully(self):
        ubuntu = getUtility(ILaunchpadCelebrities).ubuntu
        self.setUpForScriptRun(ubuntu)
        transaction.commit()
        stdout, stderr, retval = run_script(
            self.SCRIPT_PATH + " -d ubuntu")
        self.assertEqual(0, retval, "Script failure:\n" + stderr)

    def test_publishes_ubuntutest(self):
        ubuntutest = getUtility(IDistributionSet).getByName("ubuntutest")
        rootdir = self.setUpForScriptRun(ubuntutest)
        transaction.commit()
        self.makeScript(ubuntutest).main()

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
