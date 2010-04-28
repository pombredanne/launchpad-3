# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    ]


from storm.locals import Int, Reference, Storm, Unicode

from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum
from canonical.launchpad.browser.librarian import (
    ProxiedLibraryFileAlias)
from canonical.launchpad.interfaces.lpstorm import IMasterStore

from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildDerived, IPackageBuildSource)
from lp.buildmaster.model.buildbase import BuildBase
from lp.buildmaster.model.buildfarmjob import BuildFarmJobDerived
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name)
from lp.soyuz.interfaces.component import IComponentSet


class PackageBuild(BuildFarmJobDerived, Storm):
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

    policy_name = 'buildd'
    distribution = None

    def __init__(self, build_farm_job, archive, pocket,
                 dependencies=None):
        """Construct a PackageBuild."""
        super(PackageBuild, self).__init__()
        self.build_farm_job = build_farm_job
        self.archive = archive
        self.pocket = pocket
        self.dependencies = dependencies

    @classmethod
    def new(cls, job_type, virtualized, archive, pocket,
            processor=None, status=BuildStatus.BUILDING, dependencies=None):
        """See `IPackageBuildSource`."""
        store = IMasterStore(PackageBuild)

        # Create the BuildFarmJob to which the new PackageBuild
        # will delegate.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type, status, processor, virtualized)

        package_build = cls(build_farm_job, archive, pocket, dependencies)
        store.add(package_build)
        return package_build

    @property
    def current_component(self):
        """See `IPackageBuild`."""
        return getUtility(IComponentSet)[default_component_dependency_name]

    @property
    def upload_log_url(self):
        """See `IBuildBase`."""
        if self.upload_log is None:
            return None
        return ProxiedLibraryFileAlias(self.upload_log, self).http_url

    @property
    def log_url(self):
        """See `IBuildFarmJob`."""
        if self.log is None:
            return None
        return ProxiedLibraryFileAlias(self.log, self).http_url

    def getUploadLeaf(self, build_id, now=None):
        """See `IPackageBuild`."""
        return BuildBase.getUploadLeaf(build_id, now)

    def getUploadDir(self, upload_leaf):
        """See `IPackageBuild`."""
        return BuildBase.getUploadDir(upload_leaf)

    @staticmethod
    def getUploaderCommand(package_build, distro_series, upload_leaf,
                           upload_logfilename):
        """See `IPackageBuild`."""
        return BuildBase.getUploaderCommand(
            package_build, distro_series, upload_leaf, upload_logfilename)

    def getLogFromSlave(self):
        """See `IPackageBuild`."""
        return BuildBase.getLogFromSlave(self)

    @staticmethod
    def getUploadLogContent(root, leaf):
        """See `IPackageBuild`."""
        return BuildBase.getUploadLogContent(root, leaf)

    def estimateDuration(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def storeBuildInfo(self, librarian, slave_status):
        """See `IPackageBuild`."""
        return BuildBase.storeBuildInfo(self, librarian, slave_status)

    def verifySuccessfulUpload(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def storeUploadLog(self, content):
        """See `IPackageBuild`."""
        filename = "upload_%s_log.txt" % self.build_farm_job.id
        library_file = BuildBase.createUploadLog(
            self, content, filename=filename)
        self.upload_log = library_file

    def notify(self, extra_info=None):
        """See `IPackageBuild`."""
        raise NotImplementedError


class PackageBuildDerived:
    """See `IPackageBuildDerived`."""
    implements(IPackageBuildDerived)

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuildDerived`."""
        return BuildBase.handleStatus(self, status, librarian, slave_status)

    # The following private handlers currently re-use the BuildBase
    # implementation until it is no longer in use. If we find in the
    # future that it would be useful to delegate these also, they can be
    # added to IBuildFarmJob or IPackageBuild as necessary.
    def _handleStatus_OK(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_OK(
            self, librarian, slave_status, logger)

    def _handleStatus_PACKAGEFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_PACKAGEFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_DEPFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_DEPFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_CHROOTFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_CHROOTFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_BUILDERFAIL(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_BUILDERFAIL(
            self, librarian, slave_status, logger)

    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger):
        return BuildBase._handleStatus_GIVENBACK(
            self, librarian, slave_status, logger)


