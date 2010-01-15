# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation code for source package builds."""

__metaclass__ = type
__all__ = [
    'SourcePackageRecipeBuild',
    ]

import datetime

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from storm.locals import Int, Reference, Storm, TimeDelta
from storm.store import Store

from zope.component import getUtility
from zope.interface import classProvides, implements

from lp.buildmaster.interfaces.buildfarmjob import BuildFarmJobType
from lp.buildmaster.model.buildbase import BuildBase
from lp.buildmaster.model.buildfarmjob import BuildFarmJob
from lp.services.job.model.job import Job
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name,)
from lp.soyuz.interfaces.build import BuildStatus
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.sourcepackagerecipebuild import (
    ISourcePackageRecipeBuildJob, ISourcePackageRecipeBuildJobSource,
    ISourcePackageRecipeBuild, ISourcePackageRecipeBuildSource)
from lp.soyuz.model.buildqueue import BuildQueue


class SourcePackageRecipeBuild(BuildBase, Storm):
    __storm_table__ = 'SourcePackageRecipeBuild'

    implements(ISourcePackageRecipeBuild)
    classProvides(ISourcePackageRecipeBuildSource)

    build_farm_job_type = BuildFarmJobType.RECIPEBRANCHBUILD

    id = Int(primary=True)

    is_private = False

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    buildduration = TimeDelta(name='build_duration', default=None)

    builder_id = Int(name='builder', allow_none=True)
    builder = Reference(builder_id, 'Builder.id')

    buildlog_id = Int(name='build_log', allow_none=True)
    buildlog = Reference(buildlog_id, 'LibraryFileAlias.id')

    buildstate = EnumCol(
        dbName='build_state', notNull=True, schema=BuildStatus)

    @property
    def current_component(self):
        return getUtility(IComponentSet)[default_component_dependency_name]

    datecreated = UtcDateTimeCol(notNull=True, dbName='date_created')
    datebuilt = UtcDateTimeCol(notNull=False, dbName='date_built')
    date_first_dispatched = UtcDateTimeCol(notNull=False)

    distroseries_id = Int(name='distroseries', allow_none=True)
    distroseries = Reference(distroseries_id, 'DistroSeries.id')

    # XXX wgrant 2009-01-15 bug=507751: Need a DB field for this.
    dependencies = None

    sourcepackagename_id = Int(name='sourcepackagename', allow_none=True)
    sourcepackagename = Reference(
        sourcepackagename_id, 'SourcePackageName.id')

    @property
    def distribution(self):
        """See `IBuildBase`."""
        return self.distroseries.distribution

    @property
    def pocket(self):
        # JRV 2010-01-15: The database table really should have a pocket 
        # column, although this is not a big problem at the moment 
        # as recipe builds only happen for PPA's (so far). (bug 507307)
        return PackagePublishingPocket.RELEASE

    recipe_id = Int(name='recipe', allow_none=False)
    recipe = Reference(recipe_id, 'SourcePackageRecipe.id')

    requester_id = Int(name='requester', allow_none=False)
    requester = Reference(requester_id, 'Person.id')

    @property
    def buildqueue_record(self):
        """See `IBuildBase`."""
        store = Store.of(self)
        results = store.find(
            BuildQueue,
            SourcePackageRecipeBuildJob.job == BuildQueue.jobID,
            SourcePackageRecipeBuildJob.build == self.id)
        return results.one()

    def __init__(self, distroseries, sourcepackagename, recipe, requester,
                 archive, date_created=None, date_first_dispatched=None,
                 date_built=None, builder=None,
                 build_state=BuildStatus.NEEDSBUILD, build_log=None,
                 build_duration=None):
        """Construct a SourcePackageRecipeBuild."""
        super(SourcePackageRecipeBuild, self).__init__()
        self.archive = archive
        self.buildduration = build_duration
        self.buildlog = build_log
        self.builder = builder
        self.buildstate = build_state
        self.datebuilt = date_built
        self.datecreated = date_created
        self.date_first_dispatched = date_first_dispatched
        self.distroseries = distroseries
        self.recipe = recipe
        self.requester = requester
        self.sourcepackagename = sourcepackagename

    @classmethod
    def new(cls, sourcepackage, recipe, requester, archive, 
            date_created=None):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        if date_created is None:
            date_created = UTC_NOW
        spbuild = cls(
            sourcepackage.distroseries,
            sourcepackage.sourcepackagename,
            recipe,
            requester,
            archive,
            date_created=date_created)
        store.add(spbuild)
        return spbuild

    @classmethod
    def getById(cls, build_id):
        """See `ISourcePackageRecipeBuildSource`."""
        store = IMasterStore(SourcePackageRecipeBuild)
        return store.find(cls, cls.id == build_id).one()

    def makeJob(self):
        """See `ISourcePackageRecipeBuildJob`."""
        store = Store.of(self)
        job = Job()
        store.add(job)
        specific_job = getUtility(
            ISourcePackageRecipeBuildJobSource).new(self, job)
        return specific_job

    def estimateDuration(self):
        """See `IBuildBase`."""
        # XXX wgrant 2009-01-15 bug=507764: Need a more useful value.
        return datetime.timedelta(minutes=2)

    def storeUploadLog(self, content):
        return

    def notify(self, extra_info=None):
        return


class SourcePackageRecipeBuildJob(BuildFarmJob, Storm):
    classProvides(ISourcePackageRecipeBuildJobSource)
    implements(ISourcePackageRecipeBuildJob)

    __storm_table__ = 'sourcepackagerecipebuildjob'

    id = Int(primary=True)

    job_id = Int(name='job', allow_none=False)
    job = Reference(job_id, 'Job.id')

    build_id = Int(name='sourcepackage_recipe_build', allow_none=False)
    build = Reference(
        build_id, 'SourcePackageRecipeBuild.id')

    processor = None
    virtualized = True

    def __init__(self, build, job):
        super(SourcePackageRecipeBuildJob, self).__init__()
        self.build = build
        self.job = job

    @classmethod
    def new(cls, build, job):
        """See `ISourcePackageRecipeBuildJobSource`."""
        specific_job = cls(build, job)
        store = IMasterStore(SourcePackageRecipeBuildJob)
        store.add(specific_job)
        return specific_job
