# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests of `PersonMergeJob`."""

__metaclass__ = type

from zope.component import getUtility
from zope.interface.verify import verifyObject
from zope.security.proxy import removeSecurityProxy

from canonical.testing import DatabaseFunctionalLayer
from lp.registry.interfaces.persontransferjob import (
    IPersonMergeJob,
    IPersonMergeJobSource,
    )
from lp.testing import TestCaseWithFactory


class TestPersonMergeJob(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestPersonMergeJob, self).setUp()
        self.from_person = self.factory.makePerson(name='void')
        self.to_person = self.factory.makeTeam(name='gestalt')
        self.job_source = getUtility(IPersonMergeJobSource)
        self.job = self.job_source.create(
            from_person=self.from_person, to_person=self.to_person)

    def test_interface(self):
        # PersonMergeJob implements IPersonMergeJob.
        verifyObject(IPersonMergeJob, self.job)

    def test_properties(self):
        # PersonMergeJobs have a few interesting properties.
        self.assertEqual(self.from_person, self.job.from_person)
        self.assertEqual(self.from_person, self.job.minor_person)
        self.assertEqual(self.to_person, self.job.to_person)
        self.assertEqual(self.to_person, self.job.major_person)
        self.assertEqual({}, self.job.metadata)

    def test_enqueue(self):
        # Newly created jobs are enqueued.
        self.assertEqual([self.job], list(self.job_source.iterReady()))

    def test_run(self):
        # When run it merges from_person into to_person. First we need to
        # reassign from_person's email address over to to_person because
        # IPersonSet.merge() does not (yet) promise to do that.
        from_email = self.from_person.preferredemail
        removeSecurityProxy(from_email).personID = self.to_person.id
        removeSecurityProxy(from_email).accountID = self.to_person.accountID
        self.job.run()
        self.assertEqual(self.to_person, self.from_person.merged)
