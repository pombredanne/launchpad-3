# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for Soyuz build farm jobs."""

__metaclass__ = type

__all__ = [
    'IBuildFarmJob',
    'BuildFarmJobType',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _
from lazr.enum import DBEnumeratedType, DBItem
from lazr.restful.fields import Reference
from lp.soyuz.interfaces.processor import IProcessor


class BuildFarmJobType(DBEnumeratedType):
    """Soyuz build farm job type.

    An enumeration with the types of jobs that may be run on the Soyuz build
    farm.
    """

    PACKAGEBUILD = DBItem(1, """
        PackageBuildJob

        Build a source package.
        """)

    BRANCHBUILD = DBItem(2, """
        BranchBuildJob

        Build a package from a bazaar branch.
        """)

    RECIPEBRANCHBUILD = DBItem(3, """
        RecipeBranchBuildJob

        Build a package from a bazaar branch and a recipe.
        """)

    TRANSLATION = DBItem(4, """
        TranslationJob

        Perform a translation job.
        """)


class IBuildFarmJob(Interface):
    """Operations that Soyuz build farm jobs must implement."""

    def score():
        """Calculate a job score appropriate for the job type in question."""

    def getLogFileName():
        """The preferred file name for the log of this Soyuz job."""

    def getName():
        """An appropriate name for this Soyuz job."""

    def jobStarted():
        """'Job started' life cycle event, handle as appropriate."""

    def jobReset():
        """'Job reset' life cycle event, handle as appropriate."""

    def jobAborted():
        """'Job aborted' life cycle event, handle as appropriate."""

    def getPendingJobsQuery(minscore, processor, virtualized):
        """String SELECT query yielding pending jobs with given minimum score.

        This will be used for the purpose of job dispatch time estimation
        for a build job of interest (JOI).
        In order to estimate the dispatch time for the JOI we need to
        calculate the sum of the estimated durations of the *pending* jobs
        ahead of JOI.

        Depending on the build farm job type the JOI may or may not be tied
        to a particular processor type.
        Binary builds for example are always built for a specific processor
        whereas "create a source package from recipe" type jobs do not care
        about processor types or virtualization.

        When implementing this method for processor independent build farm job
        types (e.g. recipe build) you may safely ignore the `processor` and
        `virtualized` parameters.

        The SELECT query to be returned needs to select the following data

            1 - BuildQueue.job
            2 - BuildQueue.lastscore
            3 - BuildQueue.estimated_duration
            4 - Processor.id    [optional]
            5 - virtualized     [optional]

        Please do *not* order the result set since it will be UNIONed and
        ordered only then.

        Job types that are processor independent or do not care about
        virtualization should return NULL for the optional data in the result
        set.

        :param minscore: the pending jobs selected by the returned
            query should have score >= minscore
        :param processor: the job of interest (JOI) is tied to this
            processor, this information can be used to further narrow
            down the pending jobs that will result from the returned
            query. Please note: processor independent job types may
            safely ignore this parameter.
        :param virtualized: the job of interest (JOI) can only run
            on builders with this virtualization setting.
            Again, this information can be used to narrow down the
            pending jobs that will result from the returned query and
            processor independent job types may safely ignore it.
        :return: a string SELECT clause that can be used to find
            the pending jobs of the appropriate type.
        """

    processor = Reference(
        IProcessor, title=_("Processor"),
        description=_(
            "The Processor required by this build farm job. "
            "For processor independent job types please return None."))

    virtualized = Attribute(
        _(
            "The virtualization setting required by this build farm job. "
            "For job types that do not care about virtualization please "
            "return None."))
