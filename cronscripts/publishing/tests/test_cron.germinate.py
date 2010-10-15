#!/usr/bin/python

import copy
import gzip
import os
import shutil
import subprocess
import sys
import unittest

class TestCronGerminate(unittest.TestCase):
    
    DISTS = ["hardy", "lucid", "maverick"]
    COMPONENTS = ["main", "restricted", "universe", "multiverse"]
    ARCHES = ["i386", "amd64", "armel", "powerpc"]

    BASEPATH= os.path.dirname(__file__)
    ARCHIVE_DIR = os.path.join(BASEPATH, "mock-data/ubuntu-archive")
    UBUNTU_MISC_DIR = os.path.join(ARCHIVE_DIR, "ubuntu-misc")
    UBUNTU_GERMINATE_DIR = os.path.join(ARCHIVE_DIR, "ubuntu-germinate")

    def setUp(self):
        for d in [self.UBUNTU_MISC_DIR, self.UBUNTU_GERMINATE_DIR]:
            if not os.path.exists(d):
                os.makedirs(d)
        for component in self.COMPONENTS:
            # sources
            d = os.path.join(self.ARCHIVE_DIR, 
                             "ubuntu/dists/natty/%s/source" % component)
            if not os.path.exists(d):
                os.makedirs(d)
            gz = gzip.GzipFile(os.path.join(d, "Sources.gz"), "w")
            gz.close()
            
            # binaries
            for arch in self.ARCHES:
                for p in ["", "debian-installer"]:
                    d = os.path.join(
                        self.ARCHIVE_DIR,
                        "ubuntu/dists/natty/%s/%s/binary-%s" % (component, p, arch))
                    if not os.path.exists(d):
                        os.makedirs(d)
                    gz = gzip.GzipFile(os.path.join(d, "Packages.gz"), "w")
                    gz.close()

    def tearDown(self):
        for d in [self.UBUNTU_MISC_DIR, self.UBUNTU_GERMINATE_DIR]:
            shutil.rmtree(d)
        shutil.rmtree(os.path.join(self.ARCHIVE_DIR, "ubuntu/dists"))

    def test_mainenance_update(self):
        # write into more-extras.overrides to ensure its alive after we
        # mucked around
        canary = "abrowser Task mock\n"
        # build fake environment
        fake_environ = copy.copy(os.environ)
        fake_environ["TEST_ARCHIVEROOT"] = os.path.abspath(
            os.path.join(self.ARCHIVE_DIR, "ubuntu"))
        fake_environ["TEST_LAUNCHPADROOT"] = os.path.abspath(
            os.path.join(self.BASEPATH, "mock-data/mock-lp-root"))
        # use fake germinate
        fake_environ["PATH"] = "%s:%s" % (
            os.path.abspath(os.path.join(self.BASEPATH, "mock-data/mock-bin")),
            os.environ["PATH"])
        # create mock data
        for dist in self.DISTS:
            f=open(os.path.join(self.UBUNTU_MISC_DIR, 
                                "more-extra.override.%s.main" % dist), "w")
            f.write(canary)
            f.close()
        # run germiante in the fake environment
        subprocess.call([os.path.join(self.BASEPATH, "..", "cron.germinate")],
                        env=fake_environ, cwd=self.BASEPATH)
        # check the output
        for dist in self.DISTS:
            p = os.path.join(self.UBUNTU_MISC_DIR, 
                             "more-extra.override.%s.main.supported" % dist)
            self.assertTrue(os.path.exists(p))
            p = os.path.join(self.UBUNTU_MISC_DIR, 
                             "more-extra.override.%s.main" % dist)
            self.assertTrue(canary in open(p).read())
        # check if we have the data we expect
        needle = "linux-image-2.6.32-25-server/i386 Supported 5y"
        p = os.path.join(self.UBUNTU_MISC_DIR, "more-extra.override.lucid.main")
        self.assertTrue(needle in open(p).read())


if __name__ == "__main__":
    unittest.main()
