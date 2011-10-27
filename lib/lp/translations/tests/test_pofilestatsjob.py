# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for merging translations."""

__metaclass__ = type


from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    )
from lp.services.job.interfaces.job import (
    IJobSource,
    IRunnableJob,
    )
from lp.testing import TestCaseWithFactory
from lp.translations.interfaces.pofilestatsjob import IPOFileStatsJobSource
from lp.translations.interfaces.side import TranslationSide
from lp.translations.model import pofilestatsjob
from lp.translations.model.pofilestatsjob import POFileStatsJob


def runable_jobs():
    """Returns a list of the currently runnable stats update jobs.

    Provides a nicer spelling for tests than the crazy static method on the
    job class.

    The return value is listified because that's what we want for tests.
    """
    return list(POFileStatsJob.iterReady())


class TestPOFileStatsJob(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_job_interface(self):
        # Instances of POFileStatsJob are runnable jobs.
        verifyObject(IRunnableJob, POFileStatsJob(0))

    def test_source_interface(self):
        # The POFileStatsJob class is a source of POFileStatsJobs.
        verifyObject(IPOFileStatsJobSource, POFileStatsJob)
        verifyObject(IJobSource, POFileStatsJob)

    def test_run(self):
        # Running a job causes the POFile statistics to be updated.
        singular = self.factory.getUniqueString()
        pofile = self.factory.makePOFile(side=TranslationSide.UPSTREAM)
        # Create a message so we have something to have statistics about.
        self.factory.makePOTMsgSet(pofile.potemplate, singular)
        # The statistics start at 0.
        self.assertEqual(pofile.potemplate.messageCount(), 0)
        job = pofilestatsjob.schedule(pofile.id)
        # Just scheduling the job doesn't update the statistics.
        self.assertEqual(pofile.potemplate.messageCount(), 0)
        job.run()
        # Now that the job ran, the statistics have been updated.
        self.assertEqual(pofile.potemplate.messageCount(), 1)

    def test_iterReady(self):
        # The POFileStatsJob class provides a way to iterate over the jobs
        # that are ready to run.  Initially, there aren't any.
        self.assertEqual(len(list(POFileStatsJob.iterReady())), 0)
        # We need a POFile to update.
        pofile = self.factory.makePOFile(side=TranslationSide.UPSTREAM)
        # If we schedule a job, then we'll get it back.
        job = pofilestatsjob.schedule(pofile.id)
        self.assertIs(list(POFileStatsJob.iterReady())[0], job)
