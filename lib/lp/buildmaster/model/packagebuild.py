# Copyright 2010-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildMixin',
    'PackageBuildSet',
    ]


from cStringIO import StringIO

from storm.expr import Desc
from storm.locals import (
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )

from lp.buildmaster.enums import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild,
    IPackageBuildSet,
    IPackageBuildSource,
    )
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob,
    BuildFarmJobMixin,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.services.database.lpstorm import IMasterStore
from lp.services.helpers import filenameToContentType
from lp.services.librarian.browser import ProxiedLibraryFileAlias
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name,
    )
from lp.soyuz.interfaces.component import IComponentSet


class PackageBuild(Storm):
    """An implementation of `IBuildFarmJob` for package builds."""

    __storm_table__ = 'PackageBuild'

    implements(IPackageBuild)
    classProvides(IPackageBuildSource)

    id = Int(primary=True)

    archive_id = Int(name='archive', allow_none=False)
    archive = Reference(archive_id, 'Archive.id')

    pocket = DBEnum(
        name='pocket', allow_none=False,
        enum=PackagePublishingPocket)

    upload_log_id = Int(name='upload_log', allow_none=True)
    upload_log = Reference(upload_log_id, 'LibraryFileAlias.id')

    dependencies = Unicode(name='dependencies', allow_none=True)

    build_farm_job_id = Int(name='build_farm_job', allow_none=False)
    build_farm_job = Reference(build_farm_job_id, 'BuildFarmJob.id')

    # The following two properties are part of the IPackageBuild
    # interface, but need to be provided by derived classes.
    distribution = None
    distro_series = None

    def __init__(self, build_farm_job, archive, pocket,
                 dependencies=None):
        """Construct a PackageBuild."""
        super(PackageBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.archive = archive
        self.pocket = pocket
        self.dependencies = dependencies

    @classmethod
    def new(cls, job_type, virtualized, archive, pocket, processor=None,
            status=BuildStatus.NEEDSBUILD, dependencies=None,
            date_created=None, builder=None):
        """See `IPackageBuildSource`."""
        store = IMasterStore(PackageBuild)

        # Create the BuildFarmJob to which the new PackageBuild
        # will delegate.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type, status, processor, virtualized, date_created, builder)

        package_build = cls(build_farm_job, archive, pocket, dependencies)
        store.add(package_build)
        return package_build

    def destroySelf(self):
        build_farm_job = self.build_farm_job
        store = Store.of(self)
        store.remove(self)
        store.remove(build_farm_job)


class PackageBuildMixin(BuildFarmJobMixin):

    @property
    def build_farm_job(self):
        return self.package_build.build_farm_job

    @property
    def archive(self):
        return self.package_build.archive

    @property
    def pocket(self):
        return self.package_build.pocket

    @property
    def upload_log(self):
        return self.package_build.upload_log

    @property
    def dependencies(self):
        return self.package_build.dependencies

    @property
    def current_component(self):
        """See `IPackageBuild`."""
        return getUtility(IComponentSet)[default_component_dependency_name]

    @property
    def upload_log_url(self):
        """See `IPackageBuild`."""
        if self.upload_log is None:
            return None
        return ProxiedLibraryFileAlias(self.upload_log, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        if self.log is None:
            return None
        return ProxiedLibraryFileAlias(self.log, self).http_url

    @property
    def is_private(self):
        """See `IBuildFarmJob`"""
        return self.archive.private

    def estimateDuration(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def updateStatus(self, status, builder=None, slave_status=None,
                     date_started=None, date_finished=None):
        super(PackageBuildMixin, self).updateStatus(
            status, builder=builder, slave_status=slave_status,
            date_started=date_started, date_finished=date_finished)

        if (status == BuildStatus.MANUALDEPWAIT and slave_status is not None
            and slave_status.get('dependencies') is not None):
            self.package_build.dependencies = self._new_dependencies = (
                unicode(slave_status.get('dependencies')))
        else:
            self.package_build.dependencies = self._new_dependencies = None

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def createUploadLog(self, content, filename=None):
        """Creates a file on the librarian for the upload log.

        :return: ILibraryFileAlias for the upload log file.
        """
        # The given content is stored in the librarian, restricted as
        # necessary according to the targeted archive's privacy.  The content
        # object's 'upload_log' attribute will point to the
        # `LibrarianFileAlias`.

        assert self.upload_log is None, (
            "Upload log information already exists and cannot be overridden.")

        if filename is None:
            filename = 'upload_%s_log.txt' % self.id
        contentType = filenameToContentType(filename)
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        file_size = len(content)
        file_content = StringIO(content)
        restricted = self.is_private

        return getUtility(ILibraryFileAliasSet).create(
            filename, file_size, file_content, contentType=contentType,
            restricted=restricted)

    def storeUploadLog(self, content):
        """See `IPackageBuild`."""
        filename = "upload_%s_log.txt" % self.build_farm_job.id
        library_file = self.createUploadLog(content, filename=filename)
        self.package_build.upload_log = self._new_upload_log = library_file

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def getUploader(self, changes):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def queueBuild(self, suspended=False):
        """See `IPackageBuild`."""
        specific_job = self.makeJob()

        # This build queue job is to be created in a suspended state.
        if suspended:
            specific_job.job.suspend()

        duration_estimate = self.estimateDuration()
        job = specific_job.job
        processor = specific_job.processor
        queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=self.build_farm_job_type,
            job=job, processor=processor,
            virtualized=specific_job.virtualized)
        Store.of(self).add(queue_entry)
        return queue_entry


class PackageBuildSet:
    implements(IPackageBuildSet)

    def getBuildsForArchive(self, archive, status=None, pocket=None):
        """See `IPackageBuildSet`."""

        extra_exprs = []

        if status is not None:
            extra_exprs.append(BuildFarmJob.status == status)

        if pocket:
            extra_exprs.append(PackageBuild.pocket == pocket)

        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        result_set = store.find(PackageBuild,
            PackageBuild.archive == archive,
            PackageBuild.build_farm_job == BuildFarmJob.id,
            *extra_exprs)

        # When we have a set of builds that may include pending or
        # superseded builds, we order by -date_created (as we won't
        # always have a date_finished). Otherwise we can order by
        # -date_finished.
        unfinished_states = [
            BuildStatus.NEEDSBUILD,
            BuildStatus.BUILDING,
            BuildStatus.UPLOADING,
            BuildStatus.SUPERSEDED,
            ]
        if status is None or status in unfinished_states:
            result_set.order_by(
                Desc(BuildFarmJob.date_created), BuildFarmJob.id)
        else:
            result_set.order_by(
                Desc(BuildFarmJob.date_finished), BuildFarmJob.id)

        return result_set
