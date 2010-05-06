# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for Soyuz build farm jobs."""

__metaclass__ = type

__all__ = [
    'IBuildFarmJob',
    'IBuildFarmJobDerived',
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

    def getTitle():
        """A string to identify and describe the job to users."""

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


class IBuildFarmJobDerived(Interface):
    """Common functionality required by classes delegating IBuildFarmJob.

    An implementation of this class must setup the necessary delegation.
    """

    def getByJob(job):
        """Get the specific `IBuildFarmJob` for the given `Job`.

        Invoked on the specific `IBuildFarmJob`-implementing class that
        has an entry associated with `job`.
        """

    def addCandidateSelectionCriteria(processor, virtualized):
        """Provide a sub-query to refine the candidate job selection.

        Return a sub-query to narrow down the list of candidate jobs.
        The sub-query will become part of an "outer query" and is free to
        refer to the `BuildQueue` and `Job` tables already utilized in the
        latter.

        Example (please see the `BuildPackageJob` implementation for a
        complete example):

            SELECT TRUE
            FROM Archive, Build, BuildPackageJob, DistroArchSeries
            WHERE
            BuildPackageJob.job = Job.id AND
            ..

        :param processor: the type of processor that the candidate jobs are
            expected to run on.
        :param virtualized: whether the candidate jobs are expected to run on
            the `processor` natively or inside a virtual machine.
        :return: a string containing a sub-query that narrows down the list of
            candidate jobs.
        """

    def postprocessCandidate(job, logger):
        """True if the candidate job is fine and should be dispatched
        to a builder, False otherwise.

        :param job: The `BuildQueue` instance to be scrutinized.
        :param logger: The logger to use.

        :return: True if the candidate job should be dispatched
            to a builder, False otherwise.
        """

    def generateSlaveBuildCookie():
        """Produce a cookie for the slave as a token of the job it's doing.

        The cookie need not be unique, but should be hard for a
        compromised slave to guess.

        :return: a hard-to-guess ASCII string that can be reproduced
            accurately based on this job's properties.
        """

    def cleanUp():
        """Job's finished.  Delete its supporting data."""
