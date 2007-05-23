# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderSet',
    ]

import xmlrpclib
import httplib
import urllib2

from zope.interface import implements
from zope.component import getUtility

from sqlobject import (
    StringCol, ForeignKey, BoolCol, IntCol, SQLObjectNotFound)

from canonical.config import config
from canonical.buildmaster.master import BuilddMaster
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.interfaces import (
    IBuilder, IBuilderSet, IDistroArchReleaseSet, NotFoundError,
    IHasBuildRecords, IBuildSet, IBuildQueueSet)
from canonical.launchpad.webapp import urlappend
from canonical.lp.dbschema import BuildStatus


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

    def checkSlaveAlive(self):
        """See IBuilder."""
        if self.slave.echo("Test")[0] != "Test":
            raise BuildDaemonError("Failed to echo OK")

    @property
    def currentjob(self):
        """See IBuilder"""
        return getUtility(IBuildQueueSet).getByBuilder(self)

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
            current_build = self.currentjob.build
            msg = 'BUILDING %s' % current_build.title
            if not current_build.is_trusted:
                archive_name = current_build.archive.owner.name
                return '%s [%s] (%s)' % (msg, archive_name, mode)
            return '%s (%s)' % (msg, mode)

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

    def pollBuilders(self, logger, txn):
        """See IBuilderSet."""
        logger.info("Slave Scan Process Initiated.")

        buildMaster = BuilddMaster(logger, txn)

        logger.info("Setting Builders.")
        # Put every distroarchrelease we can find into the build master.
        for archrelease in getUtility(IDistroArchReleaseSet):
            buildMaster.addDistroArchRelease(archrelease)
            buildMaster.setupBuilders(archrelease)

        logger.info("Scanning Builders.")
        # Scan all the pending builds, update logtails and retrieve
        # builds where they are completed
        buildMaster.scanActiveBuilders()
        return buildMaster

    def dispatchBuilds(self, logger, buildMaster):
        """See IBuilderSet."""
        buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()

        logger.info("Dispatching Jobs.")
        # Now that we've gathered in all the builds, dispatch the pending ones
        for candidate_proc in buildCandidatesSortedByProcessor.iteritems():
            processor, buildCandidates = candidate_proc
            buildMaster.dispatchByProcessor(processor, buildCandidates)

        logger.info("Slave Scan Process Finished.")
