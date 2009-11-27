# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for Soyuz build farm jobs."""

__metaclass__ = type

__all__ = [
    'IBuildFarmJob',
    'BuildFarmJobType',
    ]

from zope.interface import Interface
from lazr.enum import DBEnumeratedType, DBItem


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

