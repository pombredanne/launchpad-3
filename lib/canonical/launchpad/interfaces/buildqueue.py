# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

"""Build interfaces."""

__metaclass__ = type

__all__ = [
    'IBuildQueue',
    'IBuildQueueSet',
    ]

from zope.interface import Interface, Attribute

from canonical.launchpad import _

class IBuildQueue(Interface):
    """A launchpad Auto Build queue entry"""

    id = Attribute("Job identifier")
    build = Attribute("The build in question")
    builder = Attribute("The builder building the build")
    created = Attribute("The datetime that the queue entry waw created")
    buildstart = Attribute("The datetime of the last build attempt")
    logtail = Attribute("The current tail of the log of the build")
    lastscore = Attribute("Last score to be computed for this job")
    archrelease = Attribute("the build DistroArchRelease")
    urgency = Attribute("SourcePackageRelease Urgency")
    component_name = Attribute("Component name where the job got published")
    archhintlist = Attribute("SourcePackageRelease archhintlist")
    name = Attribute("SourcePackageRelease name")
    version = Attribute("SourcePackageRelease version")
    files = Attribute("SourcePackageRelease files")
    builddependsindep = Attribute("SourcePackageRelease builddependsindep")
    buildduration = Attribute("The duration of the build in progress")
    manual = Attribute("whether or not the record was rescored manually")

    def manualScore(value):
        """Manually set a score value to a queue item and lock it."""

    def destroySelf():
        """Delete this entry from the database."""


class IBuildQueueSet(Interface):
    """Launchpad Auto Build queue set handler and axiliary methods"""
    title = Attribute('Title')

    def __iter__():
        """Iterate over current build jobs."""

    def __getitem__(job_id):
        """Retrieve a build job by id"""

    def count():
        """Return the number of build jobs in the queue."""

    def get(job_id):
        """Return the IBuildQueue with the given jobid."""

    def getByBuilder(builder):
        """Return an IBuildQueue instance for a builder.

        It uses selectOne to retrieve only the one possible entry being
        processed for a builder.
        If not found, return None.
        """

    def getActiveBuildJobs():
        """Return All active Build Jobs."""

    def fetchByBuildIds(build_ids):
        """Used to pre-populate the cache with reversed referred keys.

        When dealing with a group of Build records we can't use pre-join
        facility to also fetch BuildQueue records in a single query,
        because Build and BuildQueue are related with reversed keys

        Build.id = BuildQueue.build

        So this method recieves a list of Build IDs and fetches the
        correspondent BuildQueue with prejoined builder information.

        It return the SelectResults or empty list if the passed builds
        is empty, but the result isn't might to be used in call site.
        """

    def calculateCandidates(archreleases, state):
        """Return the candidates for building

        The result is a unsorted list of buildqueue items in a given state
        within a given distroarchrelease group.
        """

