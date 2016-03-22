# Copyright 2009,2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'Builder',
    'BuilderProcessor',
    'BuilderSet',
    ]

import logging

from sqlobject import (
    BoolCol,
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from storm.expr import (
    And,
    Coalesce,
    Count,
    Desc,
    Exists,
    Or,
    Select,
    SQL,
    Sum,
    )
from storm.properties import Int
from storm.references import Reference
from storm.store import Store
import transaction
from zope.component import getUtility
from zope.interface import implementer
from zope.security.proxy import removeSecurityProxy

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuilderCleanStatus,
    BuilderResetProtocol,
    BuildQueueStatus,
    )
from lp.buildmaster.interfaces.builder import (
    IBuilder,
    IBuilderSet,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSet
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.buildmaster.model.buildqueue import (
    BuildQueue,
    specific_build_farm_job_sources,
    )
from lp.buildmaster.model.processor import Processor
from lp.registry.interfaces.person import validate_public_person
from lp.services.database.bulk import (
    load,
    load_related,
    )
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    ISlaveStore,
    IStore,
    )
from lp.services.database.sqlbase import SQLBase
from lp.services.database.stormbase import StormBase
from lp.services.propertycache import (
    cachedproperty,
    get_property_cache,
    )
# XXX Michael Nelson 2010-01-13 bug=491330
# These dependencies on soyuz will be removed when getBuildRecords()
# is moved.
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuildSet
from lp.soyuz.interfaces.buildrecords import (
    IHasBuildRecords,
    IncompatibleArguments,
    )


@implementer(IBuilder, IHasBuildRecords)
class Builder(SQLBase):
    _table = 'Builder'

    _defaultOrder = ['id']

    url = StringCol(dbName='url', notNull=True)
    name = StringCol(dbName='name', notNull=True)
    title = StringCol(dbName='title', notNull=True)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
    _builderok = BoolCol(dbName='builderok', notNull=True)
    failnotes = StringCol(dbName='failnotes')
    virtualized = BoolCol(dbName='virtualized', default=True, notNull=True)
    manual = BoolCol(dbName='manual', default=False)
    vm_host = StringCol(dbName='vm_host')
    active = BoolCol(dbName='active', notNull=True, default=True)
    failure_count = IntCol(dbName='failure_count', default=0, notNull=True)
    version = StringCol(dbName='version')
    clean_status = EnumCol(
        enum=BuilderCleanStatus, default=BuilderCleanStatus.DIRTY)
    vm_reset_protocol = EnumCol(enum=BuilderResetProtocol)
    date_clean_status_changed = UtcDateTimeCol()

    def _getBuilderok(self):
        return self._builderok

    def _setBuilderok(self, value):
        self._builderok = value
        if value is True:
            self.resetFailureCount()
            self.setCleanStatus(BuilderCleanStatus.DIRTY)

    builderok = property(_getBuilderok, _setBuilderok)

    def gotFailure(self):
        """See `IBuilder`."""
        self.failure_count += 1

    def resetFailureCount(self):
        """See `IBuilder`."""
        self.failure_count = 0

    @cachedproperty
    def _processors_cache(self):
        """See `IBuilder`."""
        # This _cache method is a quick hack to get a settable
        # cachedproperty, mostly for the webservice's benefit.
        return list(Store.of(self).find(
            Processor,
            BuilderProcessor.processor_id == Processor.id,
            BuilderProcessor.builder == self).order_by(Processor.name))

    def _processors(self):
        return self._processors_cache

    def _set_processors(self, processors):
        existing = set(self.processors)
        wanted = set(processors)
        # Enable the wanted but missing.
        for processor in (wanted - existing):
            bp = BuilderProcessor()
            bp.builder = self
            bp.processor = processor
            Store.of(self).add(bp)
        # Disable the unwanted but present.
        Store.of(self).find(
            BuilderProcessor,
            BuilderProcessor.builder == self,
            BuilderProcessor.processor_id.is_in(
                processor.id for processor in existing - wanted)).remove()
        del get_property_cache(self)._processors_cache

    processors = property(_processors, _set_processors)

    @property
    def processor(self):
        """See `IBuilder`."""
        try:
            return self.processors[0]
        except IndexError:
            return None

    @processor.setter
    def processor(self, processor):
        self.processors = [processor]

    @cachedproperty
    def currentjob(self):
        """See IBuilder"""
        return getUtility(IBuildQueueSet).getByBuilder(self)

    @property
    def current_build(self):
        if self.currentjob is None:
            return None
        return self.currentjob.specific_build

    def setCleanStatus(self, status):
        """See `IBuilder`."""
        if status != self.clean_status:
            self.clean_status = status
            self.date_clean_status_changed = UTC_NOW

    def failBuilder(self, reason):
        """See IBuilder"""
        # XXX cprov 2007-04-17: ideally we should be able to notify the
        # the buildd-admins about FAILED builders. One alternative is to
        # make the buildd_cronscript (slave-scanner, in this case) to exit
        # with error, for those cases buildd-sequencer automatically sends
        # an email to admins with the script output.
        self.builderok = False
        self.failnotes = reason

    def getBuildRecords(self, build_state=None, name=None, pocket=None,
                        arch_tag=None, user=None, binary_only=True):
        """See IHasBuildRecords."""
        if binary_only:
            return getUtility(IBinaryPackageBuildSet).getBuildsForBuilder(
                self.id, build_state, name, pocket, arch_tag, user)
        else:
            if arch_tag is not None or name is not None or pocket is not None:
                raise IncompatibleArguments(
                    "The 'arch_tag', 'name', and 'pocket' parameters can be "
                    "used only with binary_only=True.")
            return getUtility(IBuildFarmJobSet).getBuildsForBuilder(
                self, status=build_state, user=user)

    def _getSlaveScannerLogger(self):
        """Return the logger instance from buildd-slave-scanner.py."""
        # XXX cprov 20071120: Ideally the Launchpad logging system
        # should be able to configure the root-logger instead of creating
        # a new object, then the logger lookups won't require the specific
        # name argument anymore. See bug 164203.
        logger = logging.getLogger('slave-scanner')
        return logger

    def acquireBuildCandidate(self):
        """See `IBuilder`."""
        candidate = self._findBuildCandidate()
        if candidate is not None:
            candidate.markAsBuilding(self)
            transaction.commit()
        return candidate

    def _findBuildCandidate(self):
        """Find a candidate job for dispatch to an idle buildd slave.

        The pending BuildQueue item with the highest score for this builder
        or None if no candidate is available.

        :return: A candidate job.
        """
        job_type_conditions = []
        job_sources = specific_build_farm_job_sources()
        for job_type, job_source in job_sources.iteritems():
            query = job_source.addCandidateSelectionCriteria(
                self.processor, self.virtualized)
            if query:
                job_type_conditions.append(
                    Or(
                        BuildFarmJob.job_type != job_type,
                        Exists(SQL(query))))

        store = IStore(self.__class__)
        candidate_jobs = store.using(BuildQueue, BuildFarmJob).find(
            (BuildQueue.id,),
            BuildFarmJob.id == BuildQueue._build_farm_job_id,
            BuildQueue.status == BuildQueueStatus.WAITING,
            Or(
                BuildQueue.processorID.is_in(Select(
                    BuilderProcessor.processor_id, tables=[BuilderProcessor],
                    where=BuilderProcessor.builder == self)),
                BuildQueue.processor == None),
            BuildQueue.virtualized == self.virtualized,
            BuildQueue.builder == None,
            And(*job_type_conditions)
            ).order_by(Desc(BuildQueue.lastscore), BuildQueue.id)

        logger = self._getSlaveScannerLogger()
        # Only try the first handful of jobs. It's much easier on the
        # database, the chance of a large prefix of the queue being
        # bad candidates is negligible, and we want reasonably bounded
        # per-cycle performance even if the prefix is large.
        for (candidate_id,) in candidate_jobs[:10]:
            candidate = getUtility(IBuildQueueSet).get(candidate_id)
            job_source = job_sources[
                removeSecurityProxy(candidate)._build_farm_job.job_type]
            candidate_approved = job_source.postprocessCandidate(
                candidate, logger)
            if candidate_approved:
                return candidate

        return None


class BuilderProcessor(StormBase):
    __storm_table__ = 'BuilderProcessor'
    __storm_primary__ = ('builder_id', 'processor_id')

    builder_id = Int(name='builder', allow_none=False)
    builder = Reference(builder_id, Builder.id)
    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, Processor.id)


@implementer(IBuilderSet)
class BuilderSet(object):
    """See IBuilderSet"""

    def __init__(self):
        self.title = "The Launchpad build farm"

    def __iter__(self):
        return iter(Builder.select())

    def getByName(self, name):
        """See IBuilderSet."""
        try:
            return Builder.selectOneBy(name=name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def __getitem__(self, name):
        return self.getByName(name)

    def new(self, processors, url, name, title, owner, active=True,
            virtualized=False, vm_host=None, vm_reset_protocol=None,
            manual=True):
        """See IBuilderSet."""
        return Builder(processors=processors, url=url, name=name, title=title,
                       owner=owner, active=active, virtualized=virtualized,
                       vm_host=vm_host, vm_reset_protocol=vm_reset_protocol,
                       _builderok=True, manual=manual)

    def get(self, builder_id):
        """See IBuilderSet."""
        return Builder.get(builder_id)

    def count(self):
        """See IBuilderSet."""
        return Builder.select().count()

    def _preloadProcessors(self, rows):
        # Grab (Builder.id, Processor.id) pairs and stuff them into the
        # Builders' processor caches.
        store = IStore(BuilderProcessor)
        pairs = list(store.using(BuilderProcessor, Processor).find(
            (BuilderProcessor.builder_id, BuilderProcessor.processor_id),
            BuilderProcessor.processor_id == Processor.id,
            BuilderProcessor.builder_id.is_in([b.id for b in rows])).order_by(
                BuilderProcessor.builder_id, Processor.name))
        load(Processor, [pid for bid, pid in pairs])
        for row in rows:
            get_property_cache(row)._processors_cache = []
        for bid, pid in pairs:
            cache = get_property_cache(store.get(Builder, bid))
            cache._processors_cache.append(store.get(Processor, pid))

    def getBuilders(self):
        """See IBuilderSet."""
        from lp.registry.model.person import Person
        rs = IStore(Builder).find(
            Builder, Builder.active == True).order_by(
                Builder.virtualized, Builder.name)

        def preload(rows):
            self._preloadProcessors(rows)
            load_related(Person, rows, ['ownerID'])
            bqs = getUtility(IBuildQueueSet).preloadForBuilders(rows)
            BuildQueue.preloadSpecificBuild(bqs)
        return DecoratedResultSet(rs, pre_iter_hook=preload)

    def getBuildQueueSizes(self):
        """See `IBuilderSet`."""
        results = ISlaveStore(BuildQueue).find((
            Count(),
            Sum(BuildQueue.estimated_duration),
            Processor,
            Coalesce(BuildQueue.virtualized, True)),
            Processor.id == BuildQueue.processorID,
            BuildQueue.status == BuildQueueStatus.WAITING).group_by(
                Processor, Coalesce(BuildQueue.virtualized, True))

        result_dict = {'virt': {}, 'nonvirt': {}}
        for size, duration, processor, virtualized in results:
            if virtualized is False:
                virt_str = 'nonvirt'
            else:
                virt_str = 'virt'
            result_dict[virt_str][processor.name] = (
                size, duration)

        return result_dict

    def getBuildersForQueue(self, processor, virtualized):
        """See `IBuilderSet`."""
        return IStore(Builder).find(
            Builder,
            Builder._builderok == True,
            Builder.virtualized == virtualized,
            BuilderProcessor.builder_id == Builder.id,
            BuilderProcessor.processor == processor)
