# Copyright 2014-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'LiveFSBuild',
    'LiveFSFile',
    ]

from datetime import timedelta

import pytz
from storm.locals import (
    Bool,
    DateTime,
    Desc,
    Int,
    JSON,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from storm.store import EmptyResultSet
from zope.component import getUtility
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.model.buildfarmjob import SpecificBuildFarmJobSourceMixin
from lp.buildmaster.model.packagebuild import PackageBuildMixin
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.registry.model.person import Person
from lp.services.config import config
from lp.services.database.bulk import load_related
from lp.services.database.constants import DEFAULT
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.features import getFeatureFlag
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.model import (
    LibraryFileAlias,
    LibraryFileContent,
    )
from lp.soyuz.interfaces.component import IComponentSet
from lp.soyuz.interfaces.livefs import (
    LIVEFS_FEATURE_FLAG,
    LiveFSFeatureDisabled,
    )
from lp.soyuz.interfaces.livefsbuild import (
    ILiveFSBuild,
    ILiveFSBuildSet,
    ILiveFSFile,
    )
from lp.soyuz.mail.livefsbuild import LiveFSBuildMailer
from lp.soyuz.model.archive import Archive


@implementer(ILiveFSFile)
class LiveFSFile(Storm):
    """See `ILiveFS`."""

    __storm_table__ = 'LiveFSFile'

    id = Int(name='id', primary=True)

    livefsbuild_id = Int(name='livefsbuild', allow_none=False)
    livefsbuild = Reference(livefsbuild_id, 'LiveFSBuild.id')

    libraryfile_id = Int(name='libraryfile', allow_none=False)
    libraryfile = Reference(libraryfile_id, 'LibraryFileAlias.id')

    def __init__(self, livefsbuild, libraryfile):
        """Construct a `LiveFSFile`."""
        super(LiveFSFile, self).__init__()
        self.livefsbuild = livefsbuild
        self.libraryfile = libraryfile


@implementer(ILiveFSBuild)
class LiveFSBuild(PackageBuildMixin, Storm):
    """See `ILiveFSBuild`."""

    __storm_table__ = 'LiveFSBuild'

    job_type = BuildFarmJobType.LIVEFSBUILD

    id = Int(name='id', primary=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')

    requester_id = Int(name='requester', allow_none=False)
    requester = Reference(requester_id, 'Person.id')

    livefs_id = Int(name='livefs', allow_none=False)
    livefs = Reference(livefs_id, 'LiveFS.id')

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    distro_arch_series_id = Int(name='distro_arch_series', allow_none=False)
    distro_arch_series = Reference(
        distro_arch_series_id, 'DistroArchSeries.id')

    pocket = DBEnum(enum=PackagePublishingPocket, allow_none=False)

    processor_id = Int(name='processor', allow_none=False)
    processor = Reference(processor_id, 'Processor.id')
    virtualized = Bool(name='virtualized')

    unique_key = Unicode(name='unique_key')

    metadata_override = JSON('json_data_override')

    _version = Unicode(name='version')

    date_created = DateTime(
        name='date_created', tzinfo=pytz.UTC, allow_none=False)
    date_started = DateTime(name='date_started', tzinfo=pytz.UTC)
    date_finished = DateTime(name='date_finished', tzinfo=pytz.UTC)
    date_first_dispatched = DateTime(
        name='date_first_dispatched', tzinfo=pytz.UTC)

    builder_id = Int(name='builder')
    builder = Reference(builder_id, 'Builder.id')

    status = DBEnum(name='status', enum=BuildStatus, allow_none=False)

    log_id = Int(name='log')
    log = Reference(log_id, 'LibraryFileAlias.id')

    upload_log_id = Int(name='upload_log')
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies')

    failure_count = Int(name='failure_count', allow_none=False)

    def __init__(self, build_farm_job, requester, livefs, archive,
                 distro_arch_series, pocket, processor, virtualized,
                 unique_key, metadata_override, version, date_created):
        """Construct a `LiveFSBuild`."""
        if not getFeatureFlag(LIVEFS_FEATURE_FLAG):
            raise LiveFSFeatureDisabled
        super(LiveFSBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.requester = requester
        self.livefs = livefs
        self.archive = archive
        self.distro_arch_series = distro_arch_series
        self.pocket = pocket
        self.processor = processor
        self.virtualized = virtualized
        self.unique_key = unique_key
        self.metadata_override = metadata_override
        self._version = version
        self.date_created = date_created
        self.status = BuildStatus.NEEDSBUILD

    @property
    def is_private(self):
        """See `IBuildFarmJob`."""
        return self.livefs.owner.private or self.archive.private

    @property
    def title(self):
        das = self.distro_arch_series
        name = self.livefs.name
        if self.unique_key is not None:
            name += " (%s)" % self.unique_key
        return "%s build of %s livefs in %s %s" % (
            das.architecturetag, name, das.distroseries.distribution.name,
            das.distroseries.getSuite(self.pocket))

    @property
    def distribution(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries.distribution

    @property
    def distro_series(self):
        """See `IPackageBuild`."""
        return self.distro_arch_series.distroseries

    @property
    def current_component(self):
        component = self.archive.default_component
        if component is not None:
            return component
        else:
            # XXX cjwatson 2014-04-22: Hardcode to universe for the time being.
            return getUtility(IComponentSet)["universe"]

    @property
    def version(self):
        """See `ILiveFSBuild`."""
        if self._version is not None:
            return self._version
        else:
            return self.date_created.strftime("%Y%m%d-%H%M%S")

    @property
    def score(self):
        """See `ILiveFSBuild`."""
        if self.buildqueue_record is None:
            return None
        else:
            return self.buildqueue_record.lastscore

    @property
    def can_be_rescored(self):
        """See `ILiveFSBuild`."""
        return (
            self.buildqueue_record is not None and
            self.status is BuildStatus.NEEDSBUILD)

    @property
    def can_be_cancelled(self):
        """See `ILiveFSBuild`."""
        if not self.buildqueue_record:
            return False

        cancellable_statuses = [
            BuildStatus.BUILDING,
            BuildStatus.NEEDSBUILD,
            ]
        return self.status in cancellable_statuses

    def rescore(self, score):
        """See `ILiveFSBuild`."""
        assert self.can_be_rescored, "Build %s cannot be rescored" % self.id
        self.buildqueue_record.manualScore(score)

    def cancel(self):
        """See `ILiveFSBuild`."""
        if not self.can_be_cancelled:
            return
        # BuildQueue.cancel() will decide whether to go straight to
        # CANCELLED, or go through CANCELLING to let buildd-manager clean up
        # the slave.
        self.buildqueue_record.cancel()

    def calculateScore(self):
        return 2510 + self.archive.relative_build_score

    def getMedianBuildDuration(self):
        """Return the median duration of our successful builds."""
        store = IStore(self)
        result = store.find(
            (LiveFSBuild.date_started, LiveFSBuild.date_finished),
            LiveFSBuild.livefs == self.livefs_id,
            LiveFSBuild.distro_arch_series == self.distro_arch_series_id,
            LiveFSBuild.status == BuildStatus.FULLYBUILT)
        result.order_by(Desc(LiveFSBuild.date_finished))
        durations = [row[1] - row[0] for row in result[:9]]
        if len(durations) == 0:
            return None
        durations.sort()
        return durations[len(durations) // 2]

    def estimateDuration(self):
        """See `IBuildFarmJob`."""
        median = self.getMedianBuildDuration()
        if median is not None:
            return median
        return timedelta(minutes=30)

    def getFiles(self):
        """See `ILiveFSBuild`."""
        result = Store.of(self).find(
            (LiveFSFile, LibraryFileAlias, LibraryFileContent),
            LiveFSFile.livefsbuild == self.id,
            LibraryFileAlias.id == LiveFSFile.libraryfile_id,
            LibraryFileContent.id == LibraryFileAlias.contentID)
        return result.order_by([LibraryFileAlias.filename, LiveFSFile.id])

    def getFileByName(self, filename):
        """See `ILiveFSBuild`."""
        if filename.endswith(".txt.gz"):
            file_object = self.log
        elif filename.endswith("_log.txt"):
            file_object = self.upload_log
        else:
            file_object = Store.of(self).find(
                LibraryFileAlias,
                LiveFSFile.livefsbuild == self.id,
                LibraryFileAlias.id == LiveFSFile.libraryfile_id,
                LibraryFileAlias.filename == filename).one()

        if file_object is not None and file_object.filename == filename:
            return file_object

        raise NotFoundError(filename)

    def addFile(self, lfa):
        """See `ILiveFSBuild`."""
        livefsfile = LiveFSFile(livefsbuild=self, libraryfile=lfa)
        IMasterStore(LiveFSFile).add(livefsfile)
        return livefsfile

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        return not self.getFiles().is_empty()

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        if not config.builddmaster.send_build_notification:
            return
        if self.status == BuildStatus.FULLYBUILT:
            return
        mailer = LiveFSBuildMailer.forStatus(self)
        mailer.sendAll()

    def lfaUrl(self, lfa):
        """Return the URL for a LibraryFileAlias in this context."""
        if lfa is None:
            return None
        return ProxiedLibraryFileAlias(lfa, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        return self.lfaUrl(self.log)

    @property
    def upload_log_url(self):
        """See `IPackageBuild`."""
        return self.lfaUrl(self.upload_log)

    def getFileUrls(self):
        return [self.lfaUrl(lfa) for _, lfa, _ in self.getFiles()]


@implementer(ILiveFSBuildSet)
class LiveFSBuildSet(SpecificBuildFarmJobSourceMixin):

    def new(self, requester, livefs, archive, distro_arch_series, pocket,
            unique_key=None, metadata_override=None, version=None,
            date_created=DEFAULT):
        """See `ILiveFSBuildSet`."""
        store = IMasterStore(LiveFSBuild)
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            LiveFSBuild.job_type, BuildStatus.NEEDSBUILD, date_created, None,
            archive)
        livefsbuild = LiveFSBuild(
            build_farm_job, requester, livefs, archive, distro_arch_series,
            pocket, distro_arch_series.processor,
            not distro_arch_series.processor.supports_nonvirtualized
            or livefs.require_virtualized or archive.require_virtualized,
            unique_key, metadata_override, version, date_created)
        store.add(livefsbuild)
        return livefsbuild

    def getByID(self, build_id):
        """See `ISpecificBuildFarmJobSource`."""
        store = IMasterStore(LiveFSBuild)
        return store.get(LiveFSBuild, build_id)

    def getByBuildFarmJob(self, build_farm_job):
        """See `ISpecificBuildFarmJobSource`."""
        return Store.of(build_farm_job).find(
            LiveFSBuild, build_farm_job_id=build_farm_job.id).one()

    def preloadBuildsData(self, builds):
        # Circular import.
        from lp.soyuz.model.livefs import LiveFS
        load_related(Person, builds, ["requester_id"])
        load_related(LibraryFileAlias, builds, ["log_id"])
        archives = load_related(Archive, builds, ["archive_id"])
        load_related(Person, archives, ["ownerID"])
        load_related(LiveFS, builds, ["livefs_id"])

    def getByBuildFarmJobs(self, build_farm_jobs):
        """See `ISpecificBuildFarmJobSource`."""
        if len(build_farm_jobs) == 0:
            return EmptyResultSet()
        rows = Store.of(build_farm_jobs[0]).find(
            LiveFSBuild, LiveFSBuild.build_farm_job_id.is_in(
                bfj.id for bfj in build_farm_jobs))
        return DecoratedResultSet(rows, pre_iter_hook=self.preloadBuildsData)
