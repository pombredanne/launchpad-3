#!/usr/bin/python
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""This is a test for the soyuz cron.germinate script."""

__metaclass__ = type

# mvo: I would love to use this, but it appears doing this import 
#      requires python-psycopg2, python-storm, python-transaction,
#      python-lazr.restful and now "windmill" that is not packaged
#      at this point I give up and let someone else with a proper
#      LP environment fix this
#from canonical.testing.layers import DatabaseFunctionalLayer

# mvo: I would love to use this, but it complains about a missing
#      import for "fixtures" and I can not find a package that
#      provides this module
#from lp.testing import TestCase # or TestCaseWithFactory
from unittest import TestCase

import copy
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class TestCronGerminate(TestCase):

    DISTS = ["hardy", "lucid", "maverick"]
    COMPONENTS = ["main", "restricted", "universe", "multiverse"]
    ARCHES = ["i386", "amd64", "armel", "powerpc"]
    BASEPATH = os.path.dirname(__file__)

    def setUp(self):
        # Setup a temp archive directory and populate it with the right
        # sub-directories.
        self.archive_dir = self.setup_mock_archive_environment()
        self.ubuntu_misc_dir = os.path.join(self.archive_dir, "ubuntu-misc")
        self.ubuntu_germinate_dir = os.path.join(self.archive_dir, "ubuntu-germinate")
        # This is what we pretend to be our current development distro, it
        # needs to be in sync with the mock lp-query-distro.py.
        self.populate_mock_archive_environment(self.archive_dir,
                                               self.COMPONENTS,
                                               self.ARCHES,
                                               "natty")

    def tearDown(self):
        shutil.rmtree(self.archive_dir)

    def create_directory_if_missing(self, directory):
        """Create the given directory if it does not exist."""
        if not os.path.exists(directory):
            os.makedirs(directory)

    def setup_mock_archive_environment(self):
        """Creates a mock archive environment and populate
           it with the subdirectories that germinate will expect.
        """
        tmpdir = tempfile.mkdtemp(prefix="tmp-cron.germinate-test")
        archive_dir = os.path.join(tmpdir, "mock-data", "ubuntu-archive")
        ubuntu_misc_dir = os.path.join(archive_dir, "ubuntu-misc")
        ubuntu_germinate_dir = os.path.join(archive_dir, "ubuntu-germinate")
        ubuntu_dists_dir = os.path.join(archive_dir, "ubuntu", "dists")
        for directory in [archive_dir, ubuntu_misc_dir,
                          ubuntu_germinate_dir, ubuntu_dists_dir]:
            self.create_directory_if_missing(directory)
        return archive_dir

    def populate_mock_archive_environment(self, archive_dir, components_list,
                                          arches_list, current_devel_distro):
        """Populates a mock archive environment with empty source packages
           and empty binary packages.
        """
        for component in components_list:
            # Create the environment for the source packages.
            targetdir = os.path.join(archive_dir,
                                     "ubuntu/dists/%s/%s/source" % (current_devel_distro, component))
            self.create_directory_if_missing(targetdir)
            gz = gzip.GzipFile(os.path.join(targetdir, "Sources.gz"), "w")
            gz.close()
            
            # Create the environment for the binary packages.
            for arch in arches_list:
                for subpath in ["", "debian-installer"]:
                    targetdir = os.path.join(
                        self.archive_dir,
                        "ubuntu/dists/%s/%s/%s/binary-%s" % (current_devel_distro, component, subpath, arch))
                    self.create_directory_if_missing(targetdir)
                    gz = gzip.GzipFile(os.path.join(targetdir, "Packages.gz"), "w")
                    gz.close()

    def test_maintenance_update(self):
        """Test the maintenance-check.py porition of the soyuz cron.germinate
           shell script by running it inside a fake environment and ensure
           that it did update the "Support" override information for
           apt-ftparchive without destroying/modifying the information
           that the "germinate" script added to it earlier.
        """
        # Write into more-extras.overrides to ensure it is alive after we
        # mucked around.
        canary = "abrowser Task mock\n"
        # Build fake environment based on the real one.
        fake_environ = copy.copy(os.environ)
        fake_environ["TEST_ARCHIVEROOT"] = os.path.abspath(
            os.path.join(self.archive_dir, "ubuntu"))
        fake_environ["TEST_LAUNCHPADROOT"] = os.path.abspath(
            os.path.join(self.BASEPATH, "mock-data/mock-lp-root"))
        # Set the PATH in the fake environment so that our mock germinate
        # is used. We could use the real germinate as well, but that will
        # slow down the tests a lot and its also not interessting for this
        # test as we do not use any of the germinate information.
        fake_environ["PATH"] = "%s:%s" % (
            os.path.abspath(os.path.join(self.BASEPATH, "mock-data/mock-bin")),
            os.environ["PATH"])
        # Create mock override data files that include the canary string
        # so that we can test later if it is still there.
        for dist in self.DISTS:
            f=open(os.path.join(self.ubuntu_misc_dir, 
                                "more-extra.override.%s.main" % dist), "w")
            f.write(canary)
            f.close()

        # Run cron.germinate in the fake environment.
        cron_germinate_path = os.path.join(
            self.BASEPATH, "..", "cron.germinate")
        subprocess.call([cron_germinate_path],
                        env=fake_environ, cwd=self.BASEPATH)

        # And check the output it generated for correctness.
        for dist in self.DISTS:
            supported_override_file = os.path.join(
                self.ubuntu_misc_dir, 
                "more-extra.override.%s.main.supported" % dist)
            self.assertTrue(os.path.exists(supported_override_file))
            main_override_file = os.path.join(
                self.ubuntu_misc_dir, 
                "more-extra.override.%s.main" % dist)
            self.assertTrue(canary in open(main_override_file).read())

        # Check here if we got the data from maintenance-check.py that
        # we expected. This is a kernel name from lucid-updates and it
        # will be valid for 5 years.
        needle = "linux-image-2.6.32-25-server/i386 Supported 5y"
        lucid_supported_override_file = os.path.join(
            self.ubuntu_misc_dir, "more-extra.override.lucid.main")
        self.assertTrue(needle in open(lucid_supported_override_file).read())


if __name__ == "__main__":
    unittest.main()
