# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tests for Diff, etc."""

__metaclass__ = type


from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.codehosting.transport import get_scanner_server
from canonical.launchpad.database.diff import *
from canonical.launchpad.interfaces import IDiff, IStaticDiff, IStaticDiffJob
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IDiff, Diff())


class TestStaticDiff(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiff, StaticDiff())


class TestStaticDiffJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_providesInterface(self):
        verifyObject(IStaticDiffJob, StaticDiffJob())

    def test_run(self):
        branch = self.factory.makeBranch()
        job = StaticDiffJob(branch=branch)
        server = get_scanner_server()
        server.setUp()
        try:
            static_diff = job.run()
        finally:
            server.tearDown()
        self.assertEqual('null:', static_diff.from_revision_id)
        self.assertEqual('rev1', static_diff.from_revision_id)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
