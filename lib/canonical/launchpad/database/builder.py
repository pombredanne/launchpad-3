# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['Builder', 'BuilderSet', 'BuildQueue',
           'BuildQueueSet']

from datetime import datetime
import xmlrpclib

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

class Builder(SQLBase):
    """See IBuilder"""
    implements(IBuilder)
    _table = 'Builder'

    processor = ForeignKey(dbName='processor', foreignKey='Processor', 
                           notNull=True)
    url = StringCol(dbName='url', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=True)
    owner = ForeignKey(dbName='owner', foreignKey='Person', notNull=True)
    builderok = BoolCol(dbName='builderok', default=True, notNull=True)
    failnotes = StringCol(dbName='failnotes')
    trusted = BoolCol(dbName='trusted', notNull=True, default=False)
    
    @property
    def currentjob(self):
        """See IBuilder"""
        return BuildQueue.selectOneBy(builderID=self.id)
    
    @property
    def slave(self):
        """See IBuilder"""
        return xmlrpclib.Server(self.url, allow_none=1)

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
    """See IBuildQueue"""
    implements(IBuildQueue)
    _table = "BuildQueue"

    build = ForeignKey(dbName='build', foreignKey='Build', notNull=True)
    builder = ForeignKey(dbName='builder', foreignKey='Builder', notNull=False)
    created = UtcDateTimeCol(dbName='created', notNull=True)
    buildstart = UtcDateTimeCol(dbName='buildstart', notNull=False)
    logtail = StringCol(dbName='logtail', notNull=False)
    lastscore = IntCol(dbName='lastscore', notNull=False)

    @property
    def partialDuration(self):
        """See IBuildQueue"""
        if self.buildstart:
            # XXX cprov 20050823
            # How to be able to use the default formaters for this field ?
            return UTC_NOW - self.buildstart

        
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
    
