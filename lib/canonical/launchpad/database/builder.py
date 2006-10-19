# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Builder',
    'BuilderSet',
    'BuildQueue',
    'BuildQueueSet'
    ]

from datetime import datetime
import xmlrpclib
import httplib
import urllib2
import pytz

from zope.interface import implements
from zope.component import getUtility

# SQLObject/SQLBase
from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.config import config
from canonical.launchpad.interfaces import (
    IBuilder, IBuilderSet, IBuildQueue, IBuildQueueSet, NotFoundError,
    IHasBuildRecords, IBuildSet
    )
from canonical.launchpad.webapp import urlappend


class TimeoutHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        """Override the standard connect() methods to set a timeout"""
        ret = httplib.HTTPConnection.connect(self)
        self.sock.settimeout(config.builddmaster.socket_timeout)
        return ret


class TimeoutHTTP(httplib.HTTP):
    _connection_class = TimeoutHTTPConnection


class TimeoutTransport(xmlrpclib.Transport):
    """XMLRPC Transport to setup a socket with defined timeout"""
    def make_connection(self, host):
        host, extra_headers, x509 = self.get_host_info(host)
        return TimeoutHTTP(host)


class BuilderSlave(xmlrpclib.Server):
    """Add in a few useful methods for the XMLRPC slave."""

    def __init__(self, urlbase):
        """Initialise a Server with specific parameter to our buildfarm."""
        self.urlbase = urlbase
        rpc_url = urlappend(urlbase, "rpc")
        xmlrpclib.Server.__init__(self, rpc_url,
                                  transport=TimeoutTransport(),
                                  allow_none=True)

    def getFile(self, sha_sum):
        """Construct a file-like object to return the named file."""
        filelocation = "filecache/%s" % sha_sum
        fileurl = urlappend(self.urlbase, filelocation)
        return urllib2.urlopen(fileurl)

class Builder(SQLBase):

    implements(IBuilder, IHasBuildRecords)
    _table = 'Builder'

    _defaultOrder = ['name']
    
    processor = ForeignKey(dbName='processor', foreignKey='Processor',
                           notNull=True)
    url = StringCol(dbName='url', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes', default=None)
    trusted = BoolCol(dbName='trusted', default=False, notNull=True)
    speedindex = IntCol(dbName='speedindex', default=0)
    manual = BoolCol(dbName='manual', default=False)

    @property
    def currentjob(self):
        """See IBuilder"""
        return BuildQueue.selectOneBy(builder=self)

    @property
    def slave(self):
        """See IBuilder"""
        return BuilderSlave(self.url)

    @property
    def status(self):
        """See IBuilder"""
        if self.manual:
            mode = 'MANUAL'
        else:
            mode = 'AUTO'

        if not self.builderok:
            return 'NOT OK : %s (%s)' % (self.failnotes, mode)

        if self.currentjob:
            return 'BUILDING %s (%s)' % (self.currentjob.build.title,
                                         mode)

        return 'IDLE (%s)' % mode

    def failbuilder(self, reason):
        """See IBuilder"""
        self.builderok = False
        self.failnotes = reason

    def getBuildRecords(self, status=None, name=None):
        """See IHasBuildRecords."""
        return getUtility(IBuildSet).getBuildsForBuilder(self.id, status, name)


class BuilderSet(object):
    """See IBuilderSet"""
    implements(IBuilderSet)

    def __init__(self):
        self.title = "The Launchpad build farm"

    def __iter__(self):
        return iter(Builder.select())

    def __getitem__(self, name):
        try:
            return Builder.selectOneBy(name=name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def new(self, processor, url, name, title, description, owner,
            builderok=True, failnotes=None, trusted=False):
        """See IBuilderSet."""
        return Builder(processor=processor, url=url, name=name, title=title,
                       description=description, owner=owner, trusted=trusted,
                       builderok=builderok, failnotes=failnotes)

    def get(self, builder_id):
        """See IBuilderSet."""
        return Builder.get(builder_id)

    def count(self):
        """See IBuilderSet."""
        return Builder.select().count()

    def getBuilders(self):
        """See IBuilderSet."""
        return Builder.select()

    def getBuildersByArch(self, arch):
        """See IBuilderSet."""
        return Builder.select('builder.processor = processor.id '
                              'AND processor.family = %d'
                              % arch.processorfamily.id,
                              clauseTables=("Processor",))


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
        """See IBuildQueue"""
        return self.build.distroarchrelease

    @property
    def urgency(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.urgency

    @property
    def component_name(self):
        """See IBuildQueue"""
        # check currently published version
        publishings = self.build.sourcepackagerelease.publishings
        if publishings.count() > 0:
            return publishings[0].component.name
        # if not found return the original component
        return self.build.sourcepackagerelease.component.name

    @property
    def archhintlist(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.architecturehintlist

    @property
    def name(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.name

    @property
    def version(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.version

    @property
    def files(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.files

    @property
    def builddependsindep(self):
        """See IBuildQueue"""
        return self.build.sourcepackagerelease.builddependsindep

    @property
    def buildduration(self):
        """See IBuildQueue"""
        if self.buildstart:
            UTC = pytz.timezone('UTC')
            now = datetime.now(UTC)
            return now - self.buildstart
        return None


class BuildQueueSet(object):
    """See IBuildQueueSet"""
    implements(IBuildQueueSet)

    def __init__(self):
        self.title = "The Launchpad build queue"

    def __iter__(self):
        return iter(BuildQueue.select())

    def __getitem__(self, job_id):
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
            return None
        clauses = ["build.distroarchrelease=%d" % d.id for d in archreleases]
        clause = " OR ".join(clauses)

        return BuildQueue.select("""
            buildqueue.build = build.id AND
            build.buildstate = %d AND
            build.distroarchrelease = distroarchrelease.id AND
            distroarchrelease.distrorelease = distrorelease.id AND
            distrorelease.distribution = distribution.id AND
            build.archive = distribution.main_archive AND
            buildqueue.builder IS NULL AND (%s)
            """ % (state.value, clause),
                clauseTables=['Build',
                              'DistroArchRelease',
                              'DistroRelease',
                              'Distribution'])

