# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for Soyuz build farm jobs."""

__metaclass__ = type

__all__ = [
    'IBuildFarmJob',
    'IBuildFarmCandidateJobSelection',
    'IBuildFarmJobDispatchEstimation',
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

    TRANSLATIONTEMPLATESBUILD = DBItem(4, """
        TranslationTemplatesBuildJob

        Generate translation templates from a bazaar branch.
        """)


class IBuildFarmJob(Interface):
    """Operations that jobs for the build farm must implement."""

    def score():
        """Calculate a job score appropriate for the job type in question."""

    def getLogFileName():
        """The preferred file name for this job's log."""

    def getName():
        """An appropriate name for this job."""

    def jobStarted():
        """'Job started' life cycle event, handle as appropriate."""

    def jobReset():
        """'Job reset' life cycle event, handle as appropriate."""

    def jobAborted():
        """'Job aborted' life cycle event, handle as appropriate."""

    processor = Reference(
        IProcessor, title=_("Processor"),
        description=_(
            "The Processor required by this build farm job. "
            "For processor-independent job types please return None."))

    virtualized = Attribute(
        _(
            "The virtualization setting required by this build farm job. "
            "For job types that do not care about virtualization please "
            "return None."))


class IBuildFarmJobDispatchEstimation(Interface):
    """Operations needed for job dipatch time estimation."""

    def composePendingJobsQuery(min_score, processor, virtualized):
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

        :param min_score: the pending jobs selected by the returned
            query should have score >= min_score.
        :param processor: the type of processor that the jobs are expected
            to run on.
        :param virtualized: whether the jobs are expected to run on the
            `processor` natively or inside a virtual machine.
        :return: a string SELECT clause that can be used to find
            the pending jobs of the appropriate type.
        """


class IBuildFarmCandidateJobSelection(Interface):
    """Operations for refining candidate job selection (optional).
    
    Job type classes that do *not* need to refine candidate job selection may
    be derived from `BuildFarmJob` which provides a base implementation of
    this interface.
    """

    def extraCandidateSelectionCriteria(processor, virtualized):
        """A 2-tuple with extra tables and clauses to be used to narrow down
        the list of candidate jobs.

        Example:
            (('Build', 'BuildPackageJob'),
             "BuildPackageJob.build = Build.id AND ..")

        :param processor: the type of processor that the candidate jobs are
            expected to run on.
        :param virtualized: whether the candidate jobs are expected to run on
            the `processor` natively or inside a virtual machine.
        :return: an (extra_tables, extra_query) tuple where `extra_tables` is
            a collection of tables that need to appear in the FROM clause of
            the combined query for `extra_query` to work. 
        """

    def checkCandidate(job, logger):
        """True if the candidate job is fine and should be dispatched
        to a builder, False otherwise.
        
        :param job: The `BuildQueue` instance to be scrutinized.
        :param logger: The logger to use.

        :return: True if the candidate job should be dispatched
            to a builder, False otherwise.
        """
