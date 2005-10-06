# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Builder', 'BuilderSet', 'BuildQueue',
           'BuildQueueSet']

from datetime import datetime
import xmlrpclib
import urlparse
import urllib2

from zope.interface import implements
from zope.exceptions import NotFoundError

# SQLObject/SQLBase
from sqlobject import (
    StringCol, ForeignKey, DateTimeCol, BoolCol, IntCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase, quote, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.launchpad.database.build import Build

from canonical.launchpad.interfaces import (
    IBuilder, IBuilderSet, IBuildQueue, IBuildQueueSet)

from canonical.lp.dbschema import EnumCol, BuildStatus

import pytz

class BuilderSlave(xmlrpclib.Server):
    """Add in a few useful methods for the XMLRPC slave."""

    def __init__(self, urlbase, *args, **kwargs):
        """Initialise..."""
        xmlrpclib.Server.__init__(self, urlparse.urljoin(urlbase,"/rpc/"),
                                  *args, **kwargs)
        self.urlbase = urlbase
    
    def getFile(self, sha_sum):
        """Construct a file-like object to return the named file."""
        return urllib2.urlopen(urlparse.urljoin(self.urlbase,
                                                "/filecache/"+sha_sum))

class Builder(SQLBase):
    implements(IBuilder)
    _table = 'Builder'

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
    
    @property
    def currentjob(self):
        """See IBuilder"""
        return BuildQueue.selectOneBy(builderID=self.id)
    
    @property
    def slave(self):
        """See IBuilder"""
        return BuilderSlave(self.url,allow_none=1)

    @property
    def status(self):
        """See IBuilder"""
        if not self.builderok:
            return 'NOT OK : %s' % self.failnotes
        if self.currentjob:
            return 'BUILDING %s' % self.currentjob.build.title
        return 'IDLE'

    def lastBuilds(self, limit=10):
        """See IBuilder"""
        return Build.select("builder=%s" % sqlvalues(self.id), limit=limit,
                            orderBy="-datebuilt")


class BuilderSet(object):
    """See IBuilderSet"""
    implements(IBuilderSet)

    def __init__(self):
        self.title = "Launchpad BuildFarm"

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


class BuildQueue(SQLBase):
    implements(IBuildQueue)
    _table = "BuildQueue"

    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    builder = ForeignKey(dbName='builder', foreignKey='Builder', default=None)
    created = UtcDateTimeCol(dbName='created', default=UTC_NOW)
    buildstart = UtcDateTimeCol(dbName='buildstart', default= None)
    logtail = StringCol(dbName='logtail', default=None)
    lastscore = IntCol(dbName='lastscore', default=0)

    @property
    def urgency(self):
        return self.build.sourcepackagerelease.urgency
    
    @property
    def component_name(self):
        return self.build.sourcepackagerelease.component.name
    
    @property
    def name(self):
        return self.build.sourcepackagerelease.name

    @property
    def version(self):
        return self.build.sourcepackagerelease.version

    @property
    def files(self):
        return self.build.sourcepackagerelease.files

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
        self.title = "Launchpad Build Queue"

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
    
