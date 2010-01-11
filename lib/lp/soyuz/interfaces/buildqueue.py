# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuildQueue',
    'IBuildQueueSet',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Choice, Datetime, Field, Timedelta

from lazr.restful.fields import Reference

from canonical.launchpad import _
from lp.buildmaster.interfaces.buildfarmjob import (
    IBuildFarmJob, BuildFarmJobType)
from lp.services.job.interfaces.job import IJob


class IBuildQueue(Interface):
    """A Launchpad Auto Build queue entry.

    This table contains work-in-progress in Buildd environment, as well as
    incoming jobs.

    It relates a pending Builds with an heuristic index (last_score) which
    is used to order build jobs in a proper way.

    When building (job dispatched) it also includes the responsible Builder
    (builder), the time it has started (buildstarted) and up to 2 Kbytes
    of the current processing log (logtail).
    """

    id = Attribute("Job identifier")
    builder = Attribute("The IBuilder instance processing this job")
    logtail = Attribute("The current tail of the log of the build")
    lastscore = Attribute("Last score to be computed for this job")
    manual = Attribute("Whether or not the job was manually scored")

    job = Reference(
        IJob, title=_("Job"), required=True, readonly=True,
        description=_("Data common to all job types."))

    job_type = Choice(
        title=_('Job type'), required=True, vocabulary=BuildFarmJobType,
        description=_("The type of this job."))

    required_build_behavior = Field(
        title=_('The builder behavior required to run this job.'),
        required=False, readonly=True)

    specific_job_classes = Field(
        title=_('Job classes that may run on the build farm.'),
        required=True, readonly=True)

    estimated_duration = Timedelta(
        title=_("Estimated Job Duration"), required=True,
        description=_("Estimated job duration interval."))

    def manualScore(value):
        """Manually set a score value to a queue item and lock it."""

    def score():
        """The job score calculated for the job type in question."""

    def destroySelf():
        """Delete this entry from the database."""

    def getLogFileName():
        """Get the preferred filename for the buildlog of this build."""

    def markAsBuilding(builder):
        """Set this queue item to a 'building' state."""

    def reset():
        """Reset this job, so it can be re-dispatched."""

    def updateBuild_IDLE(build_id, build_status, logtail,
                         filemap, dependencies, logger):
        """Somehow the builder forgot about the build job.

        Log this and reset the record.
        """

    def updateBuild_BUILDING(build_id, build_status, logtail, filemap,
                             dependencies, logger):
        """Build still building, collect the logtail"""

    def updateBuild_ABORTING(buildid, build_status, logtail, filemap,
                             dependencies, logger):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """

    def updateBuild_ABORTED(buildid, build_status, logtail, filemap,
                            dependencies, logger):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """

    specific_job = Reference(
        IBuildFarmJob, title=_("Job"),
        description=_("Data and operations common to all build farm jobs."))

    def setDateStarted(timestamp):
        """Sets the date started property to the given value."""

    date_started = Datetime(
        title=_('Start time'),
        description=_('Time when the job started.'))


class IBuildQueueSet(Interface):
    """Launchpad Auto Build queue set handler and auxiliary methods."""

    title = Attribute('Title')

    def __iter__():
        """Iterate over current build jobs."""

    def __getitem__(job_id):
        """Retrieve a build job by id."""

    def count():
        """Return the number of build jobs in the queue."""

    def get(job_id):
        """Return the IBuildQueue with the given job_id."""

    def getByBuilder(builder):
        """Return an IBuildQueue instance for a builder.

        Retrieve the only one possible entry being processed for a given
        builder. If not found, return None.
        """

    def getActiveBuildJobs():
        """Return All active Build Jobs."""

    def calculateCandidates(archseries):
        """Return the BuildQueue records for the given archseries.

        Returns a selectRelease of BuildQueue items sorted by descending
        'lastscore' within the given archseries.

        'archseries' argument should be a list of DistroArchSeries and it is
        asserted to not be None/empty.
        """

    def getForBuilds(build_ids):
        """Return the IBuildQueue instance for the IBuild IDs at hand.

        Retrieve the build queue and related builder rows associated with the
        builds in question where they exist.
        """
