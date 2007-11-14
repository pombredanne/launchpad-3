# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet'
    ]

from datetime import datetime
import logging
import pytz

from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)

from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    BuildStatus, IBuildQueue, IBuildQueueSet, NotFoundError,
    SourcePackageUrgency)


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"
    _defaultOrder = "id"

    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    builder = ForeignKey(dbName='builder', foreignKey='Builder', default=None)
    created = UtcDateTimeCol(dbName='created', default=UTC_NOW)
    buildstart = UtcDateTimeCol(dbName='buildstart', default= None)
    logtail = StringCol(dbName='logtail', default=None)
    lastscore = IntCol(dbName='lastscore', default=0)
    manual = BoolCol(dbName='manual', default=False)

    def manualScore(self, value):
        """See IBuildQueue."""
        self.lastscore = value
        self.manual = True

    @property
    def archseries(self):
        """See IBuildQueue."""
        return self.build.distroarchseries

    @property
    def urgency(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.urgency

    @property
    def archhintlist(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.architecturehintlist

    @property
    def name(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.name

    @property
    def version(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.version

    @property
    def files(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.files

    @property
    def builddependsindep(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.builddependsindep

    @property
    def buildduration(self):
        """See IBuildQueue."""
        if self.buildstart:
            UTC = pytz.timezone('UTC')
            now = datetime.now(UTC)
            return now - self.buildstart
        return None

    @property
    def is_trusted(self):
        """See IBuildQueue"""
        return self.build.is_trusted

    def score(self):
        """See IBuildQueue"""
        # Grab any logger instance available.
        logger = logging.getLogger()
    
        if self.manual:
            logger.debug(
                "%s (%d) MANUALLY RESCORED" % (self.name, self.lastscore))
            return

        score_componentname = {
            'multiverse': 0,
            'universe': 250,
            'restricted': 750,
            'main': 1000,
            'partner' : 1250,
            }

        score_urgency = {
            SourcePackageUrgency.LOW: 5,
            SourcePackageUrgency.MEDIUM: 10,
            SourcePackageUrgency.HIGH: 15,
            SourcePackageUrgency.EMERGENCY: 20,
            }

        # Define a table we'll use to calculate the score based on the time
        # in the build queue.  The table is a sorted list of (upper time
        # limit in seconds, score) tuples.
        queue_time_scores = [
            (14400, 100),
            (7200, 50),
            (3600, 20),
            (1800, 15),
            (900, 10),
            (300, 5),
        ]

        score = 0
        msg = "%s (%d) -> " % (self.build.title, self.lastscore)

        # Calculates the urgency-related part of the score.
        score += score_urgency[self.urgency]
        msg += "U+%d " % score_urgency[self.urgency]

        # Calculates the component-related part of the score.
        score += score_componentname[self.build.current_component.name]
        msg += "C+%d " % score_componentname[
            self.build.current_component.name]

        # Calculates the build queue time component of the score.
        right_now = datetime.now(pytz.timezone('UTC'))
        eta = right_now - self.created
        for limit, dep_score in queue_time_scores:
            if eta.seconds > limit:
                score += dep_score
                msg += "T+%d " % dep_score
                break
        else:
            msg += "T+0 "

        # Store current score value.
        self.lastscore = score

        logger.debug("%s= %d" % (msg, self.lastscore))

    def getLogFileName(self):
        """See IBuildQueue"""
        sourcename = self.build.sourcepackagerelease.name
        version = self.build.sourcepackagerelease.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = self.build.buildstate.name

        dar = self.build.distroarchseries
        distroname = dar.distroseries.distribution.name
        distroseriesname = dar.distroseries.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTROSeries>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        return ('buildlog_%s-%s-%s.%s_%s_%s.txt' % (
            distroname, distroseriesname, archname, sourcename, version, state
            ))

    def markAsBuilding(self, builder):
        """See `IBuildQueue`."""
        self.builder = builder
        self.buildstart = UTC_NOW
        self.build.buildstate = BuildStatus.BUILDING

    def updateBuild_IDLE(self, build_id, build_status, logtail,
                         filemap, dependencies, logger):
        """See IBuildQueue."""
        logger.warn(
            "Builder %s forgot about build %s -- resetting buildqueue record"
            % (self.builder.url, self.build.title))
        self.builder = None
        self.buildstart = None
        self.build.buildstate = BuildStatus.NEEDSBUILD

    def updateBuild_BUILDING(self, build_id, build_status,
                             logtail, filemap, dependencies, logger):
        """See IBuildQueue"""
        self.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, buildid, build_status,
                             logtail, filemap, dependencies, logger):
        """See IBuildQueue"""
        self.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, buildid, build_status,
                            logtail, filemap, dependencies, logger):
        """See IBuildQueue"""
        self.builder.cleanSlave()
        self.builder = None
        self.buildstart = None
        self.build.buildstate = BuildStatus.BUILDING


class BuildQueueSet(object):
    """See IBuildQueueSet"""
    implements(IBuildQueueSet)

    def __init__(self):
        self.title = "The Launchpad build queue"

    def __iter__(self):
        """See IBuildQueueSet."""
        return iter(BuildQueue.select())

    def __getitem__(self, job_id):
        """See IBuildQueueSet."""
        try:
            return BuildQueue.get(job_id)
        except SQLObjectNotFound:
            raise NotFoundError(job_id)

    def get(self, job_id):
        """See IBuildQueueSet."""
        return BuildQueue.get(job_id)

    def count(self):
        """See IBuildQueueSet."""
        return BuildQueue.select().count()

    def getByBuilder(self, builder):
        """See IBuildQueueSet."""
        return BuildQueue.selectOneBy(builder=builder)

    def getActiveBuildJobs(self):
        """See IBuildQueueSet."""
        return BuildQueue.select('buildstart is not null')

    def fetchByBuildIds(self, build_ids):
        """See IBuildQueueSet."""
        if len(build_ids) == 0:
            return []

        return BuildQueue.select(
            "buildqueue.build IN %s" % ','.join(sqlvalues(build_ids)),
            prejoins=['builder'])

    def calculateCandidates(self, archserieses, state):
        """See IBuildQueueSet."""
        if not archserieses:
            # return an empty SQLResult instance to make the callsites happy.
            return BuildQueue.select("1=2")

        if not isinstance(archserieses, list):
            archseries = [archserieses]
        arch_ids = [d.id for d in archserieses]

        candidates = BuildQueue.select("""
        build.distroarchseries IN %s AND
        build.buildstate = %s AND
        buildqueue.build = build.id AND
        buildqueue.builder IS NULL
        """ % sqlvalues(arch_ids, state), clauseTables=['Build'])

        return candidates
