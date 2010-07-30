# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    'PackageBuildSet',
    ]


import logging

from lazr.delegates import delegates
from storm.expr import Desc
from storm.locals import Int, Reference, Storm, Unicode
from zope.component import getUtility
from zope.interface import classProvides, implements

from canonical.database.enumcol import DBEnum
from canonical.launchpad.browser.librarian import (
    ProxiedLibraryFileAlias)
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import (
        IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)

from lp.buildmaster.interfaces.buildbase import (BUILDD_MANAGER_LOG_NAME,
    BuildStatus)
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild, IPackageBuildSet, IPackageBuildSource)
from lp.buildmaster.model.buildbase import BuildBase
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob, BuildFarmJobDerived)
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
    def new(cls, job_type, virtualized, archive, pocket,
            processor=None, status=BuildStatus.NEEDSBUILD, dependencies=None,
            date_created=None):
        """See `IPackageBuildSource`."""
        store = IMasterStore(PackageBuild)

        # Create the BuildFarmJob to which the new PackageBuild
        # will delegate.
        build_farm_job = getUtility(IBuildFarmJobSource).new(
            job_type, status, processor, virtualized, date_created)

        package_build = cls(build_farm_job, archive, pocket, dependencies)
        store.add(package_build)
        return package_build

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

    def getUploadDirLeaf(self, build_cookie, now=None):
        """See `IPackageBuild`."""
        return BuildBase.getUploadDirLeaf(build_cookie, now)

    def getUploadDir(self, upload_leaf):
        """See `IPackageBuild`."""
        return BuildBase.getUploadDir(upload_leaf)

    @staticmethod
    def getUploaderCommand(package_build, upload_leaf, upload_logfilename):
        """See `IPackageBuild`."""
        return BuildBase.getUploaderCommand(
            package_build, upload_leaf, upload_logfilename)

    @staticmethod
    def getLogFromSlave(package_build):
        """See `IPackageBuild`."""
        return BuildBase.getLogFromSlave(package_build)

    @staticmethod
    def getUploadLogContent(root, leaf):
        """See `IPackageBuild`."""
        return BuildBase.getUploadLogContent(root, leaf)

    def estimateDuration(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    @staticmethod
    def storeBuildInfo(package_build, librarian, slave_status):
        """See `IPackageBuild`."""
        return BuildBase.storeBuildInfo(package_build, librarian,
                                        slave_status)

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

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def queueBuild(self, suspended=False):
        """See `IPackageBuild`."""
        raise NotImplementedError


class PackageBuildDerived:
    """Setup the delegation for package build.

    This class also provides some common implementation for handling
    build status.
    """
    delegates(IPackageBuild, context="package_build")

    def queueBuild(self, suspended=False):
        """See `IPackageBuild`."""
        return BuildBase.queueBuild(self, suspended=suspended)

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)
        method = getattr(self, '_handleStatus_' + status, None)
        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, self.buildqueue_record.builder.url))
            return
        method(librarian, slave_status, logger)

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
            BuildStatus.SUPERSEDED]
        if status is None or status in unfinished_states:
            result_set.order_by(
                Desc(BuildFarmJob.date_created), BuildFarmJob.id)
        else:
            result_set.order_by(
                Desc(BuildFarmJob.date_finished), BuildFarmJob.id)

        return result_set
