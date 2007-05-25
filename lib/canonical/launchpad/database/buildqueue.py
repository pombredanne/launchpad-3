# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'BuildQueue',
    'BuildQueueSet'
    ]

from datetime import datetime
import pytz

from zope.interface import implements

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)

from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
    IBuildQueue, IBuildQueueSet, NotFoundError)
from canonical.lp.dbschema import BuildStatus

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
    def archrelease(self):
        """See IBuildQueue."""
        return self.build.distroarchrelease

    @property
    def urgency(self):
        """See IBuildQueue."""
        return self.build.sourcepackagerelease.urgency

    @property
    def component_name(self):
        """See IBuildQueue."""
        # check currently published version
        publishings = self.build.sourcepackagerelease.publishings
        if publishings.count() > 0:
            return publishings[0].component.name
        # if not found return the original component
        return self.build.sourcepackagerelease.component.name

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

    def getLogFileName(self):
        """Get the preferred filename for the buildlog of this build."""
        # XXX Robert Collins 20070526: this should be directly tested.
        sourcename = self.build.sourcepackagerelease.name
        version = self.build.sourcepackagerelease.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = self.build.buildstate.name

        dar = self.build.distroarchrelease
        distroname = dar.distrorelease.distribution.name
        distroreleasename = dar.distrorelease.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTRORELEASE>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        return ('buildlog_%s-%s-%s.%s_%s_%s.txt' % (
            distroname, distroreleasename, archname, sourcename, version, state
            ))

    def updateBuild_IDLE(self, slave, build_id, build_status, logtail,
                         filemap, dependencies, logger):
        """See IBuildQueue."""
        logger.warn(
            "Builder on %s is Dory AICMFP. Builder forgot about build %s "
            "-- resetting buildqueue record"
            % (self.builder.url, self.build.title))
        self.builder = None
        self.buildstart = None
        self.build.buildstate = BuildStatus.NEEDSBUILD

    def updateBuild_BUILDING(self, slave, build_id, build_status,
                             logtail, filemap, dependencies, logger):
        """See IBuildQueue"""
        self.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, slave, buildid, build_status,
                             logtail, filemap, dependencies, logger):
        """See IBuildQueue"""
        self.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, slave, buildid, build_status,
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

    def calculateCandidates(self, archreleases, state):
        """See IBuildQueueSet."""
        if not archreleases:
            # return an empty SQLResult instance to make the callsites happy.
            return BuildQueue.select("1=2")

        if not isinstance(archreleases, list):
            archrelease = [archreleases]
        arch_ids = [d.id for d in archreleases]

        candidates = BuildQueue.select("""
        build.distroarchrelease IN %s AND
        build.buildstate = %s AND
        buildqueue.build = build.id AND
        buildqueue.builder IS NULL
        """ % sqlvalues(arch_ids, state), clauseTables=['Build'])

        return candidates
