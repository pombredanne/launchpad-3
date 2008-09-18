# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from unittest import TestLoader

from canonical.testing import LaunchpadZopelessLayer

from canonical.launchpad.database import Job, JobDependency
from canonical.launchpad.interfaces import IJob
from canonical.launchpad.testing import TestCase
from canonical.launchpad.webapp.testing import verifyObject


class TestJob(TestCase):

    layer = LaunchpadZopelessLayer

    def test_implements_IJob(self):
        verifyObject(IJob, Job())

    def test_dependencies(self):
        job1 = Job()
        job2 = Job()
        job2.prerequisites.add(job1)
        self.assertTrue(job2 in job1.dependants)

    def test_destroySelf_of_prerequisite(self):
        job1 = Job()
        job2 = Job()
        job2.prerequisites.add(job1)
        job1.destroySelf()
        self.assertEqual(0, job2.prerequisites.count())

    def test_destroySelf_of_dependant(self):
        job1 = Job()
        job2 = Job()
        job2.dependants.add(job1)
        job1.destroySelf()
        self.assertEqual(0, job2.dependants.count())


class TestJobDependency(TestCase):

    layer = LaunchpadZopelessLayer

    def test_correct_columns(self):
        job1 = Job()
        job2 = Job()
        JobDependency(prerequisite=job1.id, dependant=job2.id)
        self.assertTrue(job1 in job2.prerequisites)
        self.assertTrue(job1 not in job2.dependants)
        self.assertTrue(job2 in job1.dependants)
        self.assertTrue(job2 not in job1.prerequisites)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
