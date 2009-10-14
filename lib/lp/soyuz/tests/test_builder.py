# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test Builder features."""

import unittest

from zope.component import getUtility

from canonical.testing import LaunchpadZopelessLayer
from lp.soyuz.interfaces.builder import IBuilderSet
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.tests.test_publishing import SoyuzTestPublisher
from lp.testing import TestCaseWithFactory


class TestFindBuildCandidate(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Publish some builds for the test archive."""
        super(TestFindBuildCandidate, self).setUp()
        self.publisher = SoyuzTestPublisher()
        self.publisher.prepareBreezyAutotest()

        # Create two PPAs and add some builds to each.
        self.ppa_joe = self.factory.makeArchive(name="joesppa")
        self.ppa_jim = self.factory.makeArchive(name="jimsppa")

        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()
        self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_joe).createMissingBuilds()

        self.publisher.getPubSource(
            sourcename="gedit", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_jim).createMissingBuilds()
        self.publisher.getPubSource(
            sourcename="firefox", status=PackagePublishingStatus.PUBLISHED,
            archive=self.ppa_jim).createMissingBuilds()

        # Create two i386 builders ready to build PPA builds.
        builder_set = getUtility(IBuilderSet)
        self.builder1 = self.factory.makeBuilder(name='bob2')
        self.builder2 = self.factory.makeBuilder(name='frog2')

        # Grab the first build, ensure that it is what we expect
        # (ie. the first build from joesppa) and set it building.
        self.first_job = self.builder1.findBuildCandidate()
        self.failUnlessEqual('joesppa', self.first_job.build.archive.name)
        self.failUnlessEqual(
            u'i386 build of gedit 666 in ubuntutest breezy-autotest RELEASE',
            self.first_job.build.title)
        self.first_job.build.buildstate = BuildStatus.BUILDING
        self.first_job.build.builder = self.builder1

    def test_findBuildCandidate_first_build_started(self):
        # Once a build for an ppa+arch has started, a second one for the
        # same ppa+arch will not be a candidate.
        next_job = self.builder2.findBuildCandidate()
        self.failIfEqual('joesppa', next_job.build.archive.name)

    def test_findBuildCandidate_first_build_finished(self):
        # When joe's first ppa build finishes, his second i386 build
        # will be the next build candidate.
        self.first_job.build.buildstate = BuildStatus.FAILEDTOBUILD
        next_job = self.builder2.findBuildCandidate()
        self.failUnlessEqual('joesppa', next_job.build.archive.name)

    def test_findBuildCandidate_for_private_ppa(self):
        # If a ppa is private it will be able to have parallel builds
        # for the one architecture.
        self.ppa_joe.private = True
        self.ppa_joe.buildd_secret = 'sekrit'
        next_job = self.builder2.findBuildCandidate()
        self.failUnlessEqual('joesppa', next_job.build.archive.name)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
