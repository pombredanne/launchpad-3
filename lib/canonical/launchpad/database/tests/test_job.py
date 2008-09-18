# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.database import Job
from canonical.launchpad.interfaces import IJob
from canonical.launchpad.testing import TestCaseWithFactory
from canonical.launchpad.webapp.testing import verifyObject


class TestJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        verifyObject(IJob, Job())


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
