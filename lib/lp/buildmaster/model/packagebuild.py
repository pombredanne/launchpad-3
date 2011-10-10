# Copyright 2010-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'PackageBuild',
    'PackageBuildDerived',
    'PackageBuildSet',
    ]


from cStringIO import StringIO
import datetime
import logging
import os.path

from lazr.delegates import delegates
import pytz
from storm.expr import Desc
from storm.locals import (
    Int,
    Reference,
    Store,
    Storm,
    Unicode,
    )
import transaction
from zope.component import getUtility
from zope.interface import (
    classProvides,
    implements,
    )
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.enumcol import DBEnum
from canonical.launchpad.browser.librarian import ProxiedLibraryFileAlias
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.buildfarmjob import IBuildFarmJobSource
from lp.buildmaster.interfaces.packagebuild import (
    IPackageBuild,
    IPackageBuildSet,
    IPackageBuildSource,
    )
from lp.buildmaster.model.buildfarmjob import (
    BuildFarmJob,
    BuildFarmJobDerived,
    )
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.database.transaction_policy import DatabaseTransactionPolicy
from lp.soyuz.adapters.archivedependencies import (
    default_component_dependency_name,
    )
from lp.soyuz.interfaces.component import IComponentSet


SLAVE_LOG_FILENAME = 'buildlog'


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

    def destroySelf(self):
        build_farm_job = self.build_farm_job
        store = Store.of(self)
        store.remove(self)
        store.remove(build_farm_job)

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
        if now is None:
            now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        return '%s-%s' % (timestamp, build_cookie)

    @staticmethod
    def getLogFromSlave(package_build):
        """See `IPackageBuild`."""
        builder = package_build.buildqueue_record.builder
        d = builder.transferSlaveFileToLibrarian(
            SLAVE_LOG_FILENAME,
            package_build.buildqueue_record.getLogFileName(),
            package_build.is_private)
        return d

    def estimateDuration(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    @staticmethod
    def storeBuildInfo(build, librarian, slave_status):
        """See `IPackageBuild`."""
        def got_log(lfa_id):
            # log, builder and date_finished are read-only, so we must
            # currently remove the security proxy to set them.
            transaction.commit()
            with DatabaseTransactionPolicy(read_only=False):
                naked_build = removeSecurityProxy(build)
                naked_build.log = lfa_id
                naked_build.builder = build.buildqueue_record.builder
                # XXX cprov 20060615 bug=120584: Currently buildduration
                # includes the scanner latency.  It should really be asking
                # the slave for the duration spent building locally.
                naked_build.date_finished = datetime.datetime.now(pytz.UTC)
                if slave_status.get('dependencies') is not None:
                    build.dependencies = unicode(
                        slave_status.get('dependencies'))
                else:
                    build.dependencies = None
                transaction.commit()

        d = build.getLogFromSlave(build)
        return d.addCallback(got_log)

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

    def getBuildCookie(self):
        """See `IPackageBuild`."""
        raise NotImplementedError

    def getUploader(self, changes):
        """See `IPackageBuild`."""
        raise NotImplementedError


class PackageBuildDerived:
    """Setup the delegation for package build.

    This class also provides some common implementation for handling
    build status.
    """
    delegates(IPackageBuild, context="package_build")

    # The list of build status values for which email notifications are
    # allowed to be sent. It is up to each callback as to whether it will
    # consider sending a notification but it won't do so if the status is not
    # in this list.
    ALLOWED_STATUS_NOTIFICATIONS = ['OK', 'PACKAGEFAIL', 'CHROOTFAIL']

    def getBuildCookie(self):
        """See `IPackageBuild`."""
        return '%s-%s' % (self.job_type.name, self.id)

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

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
        from lp.buildmaster.manager import BUILDD_MANAGER_LOG_NAME
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)
        send_notification = status in self.ALLOWED_STATUS_NOTIFICATIONS
        method = getattr(self, '_handleStatus_' + status, None)
        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, self.buildqueue_record.builder.url))
            return
        d = method(librarian, slave_status, logger, send_notification)
        return d

    def _destroy_buildqueue_record(self, unused_arg):
        """Destroy this build's `BuildQueue` record."""
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            self.buildqueue_record.destroySelf()
            transaction.commit()

    def _release_builder_and_remove_queue_item(self):
        # Release the builder for another job.
        d = self.buildqueue_record.builder.cleanSlave()
        # Remove BuildQueue record.
        return d.addCallback(self._destroy_buildqueue_record)

    def _notify_if_appropriate(self, appropriate=True, extra_info=None):
        """If `appropriate`, call `self.notify` in a write transaction."""
        if not appropriate:
            return
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            self.notify(extra_info=extra_info)
            transaction.commit()

    def _handleStatus_OK(self, librarian, slave_status, logger,
                         send_notification):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        filemap = slave_status['filemap']

        logger.info("Processing successful build %s from builder %s" % (
            self.buildqueue_record.specific_job.build.title,
            self.buildqueue_record.builder.name))

        # If this is a binary package build, discard it if its source is
        # no longer published.
        if self.build_farm_job_type == BuildFarmJobType.PACKAGEBUILD:
            build = self.buildqueue_record.specific_job.build
            if not build.current_source_publication:
                transaction.commit()
                with DatabaseTransactionPolicy(read_only=False):
                    build.status = BuildStatus.SUPERSEDED
                    transaction.commit()
                return self._release_builder_and_remove_queue_item()

        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distro_series.canUploadToPocket(self.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (self.title, self.id, self.pocket.name))

        # Ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)

        # Create a single directory to store build result files.
        upload_leaf = self.getUploadDirLeaf(self.getBuildCookie())
        grab_dir = os.path.join(root, "grabbing", upload_leaf)
        logger.debug("Storing build result at '%s'" % grab_dir)

        # Build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #       <archive_id>/distribution_name
        # for all destination archive types.
        upload_path = os.path.join(
            grab_dir, str(self.archive.id), self.distribution.name)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(self.buildqueue_record.builder.slave)
        successful_copy_from_slave = True
        filenames_to_download = {}
        for filename in filemap:
            logger.info("Grabbing file: %s" % filename)
            out_file_name = os.path.join(upload_path, filename)
            # If the evaluated output file name is not within our
            # upload path, then we don't try to copy this or any
            # subsequent files.
            if not os.path.realpath(out_file_name).startswith(upload_path):
                successful_copy_from_slave = False
                logger.warning(
                    "A slave tried to upload the file '%s' "
                    "for the build %d." % (filename, self.id))
                break
            filenames_to_download[filemap[filename]] = out_file_name

        def build_info_stored(ignored):
            # We only attempt the upload if we successfully copied all the
            # files from the slave.
            if successful_copy_from_slave:
                logger.info(
                    "Gathered %s %d completely. "
                    "Moving %s to uploader queue.",
                    self.__class__.__name__, self.id, upload_leaf)
                target_dir = os.path.join(root, "incoming")
                resulting_status = BuildStatus.UPLOADING
            else:
                logger.warning(
                    "Copy from slave for build %s was unsuccessful.",
                    self.id)
                target_dir = os.path.join(root, "failed")
                resulting_status = BuildStatus.FAILEDTOUPLOAD

            transaction.commit()
            with DatabaseTransactionPolicy(read_only=False):
                self.status = resulting_status
                transaction.commit()

            if not successful_copy_from_slave:
                self._notify_if_appropriate(
                    send_notification, "Copy from slave was unsuccessful.")

            if not os.path.exists(target_dir):
                os.mkdir(target_dir)

            # Release the builder for another job.
            d = self._release_builder_and_remove_queue_item()

            # Move the directory used to grab the binaries into
            # the incoming directory so the upload processor never
            # sees half-finished uploads.
            os.rename(grab_dir, os.path.join(target_dir, upload_leaf))

            return d

        d = slave.getFiles(filenames_to_download)
        # Store build information, build record was already updated during
        # the binary upload.
        d.addCallback(
            lambda x: self.storeBuildInfo(self, librarian, slave_status))
        d.addCallback(build_info_stored)
        return d

    def _handleStatus_PACKAGEFAIL(self, librarian, slave_status, logger,
                                  send_notification):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            self.status = BuildStatus.FAILEDTOBUILD
            transaction.commit()

        def build_info_stored(ignored):
            self._notify_if_appropriate(send_notification)
            d = self.buildqueue_record.builder.cleanSlave()
            return d.addCallback(self._destroy_buildqueue_record)

        d = self.storeBuildInfo(self, librarian, slave_status)
        return d.addCallback(build_info_stored)

    def _handleStatus_DEPFAIL(self, librarian, slave_status, logger,
                              send_notification):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        self.status = BuildStatus.MANUALDEPWAIT

        def build_info_stored(ignored):
            logger.critical("***** %s is MANUALDEPWAIT *****"
                            % self.buildqueue_record.builder.name)
            self._notify_if_appropriate(send_notification)
            d = self.buildqueue_record.builder.cleanSlave()
            return d.addCallback(self._destroy_buildqueue_record)

        d = self.storeBuildInfo(self, librarian, slave_status)
        return d.addCallback(build_info_stored)

    def _handleStatus_CHROOTFAIL(self, librarian, slave_status, logger,
                                 send_notification):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        self.status = BuildStatus.CHROOTWAIT

        def build_info_stored(ignored):
            logger.critical(
                "***** %s is CHROOTWAIT *****",
                self.buildqueue_record.builder.name)

            self._notify_if_appropriate(send_notification)
            d = self.buildqueue_record.builder.cleanSlave()
            return d.addCallback(self._destroy_buildqueue_record)

        d = self.storeBuildInfo(self, librarian, slave_status)
        return d.addCallback(build_info_stored)

    def _reset_buildqueue_record(self, ignored_arg=None):
        """Reset the `BuildQueue` record, in a write transaction."""
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            self.buildqueue_record.reset()
            transaction.commit()

    def _handleStatus_BUILDERFAIL(self, librarian, slave_status, logger,
                                  send_notification):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % self.buildqueue_record.builder.name)
        self.buildqueue_record.builder.failBuilder(
            "Builder returned BUILDERFAIL when asked for its status")

        d = self.storeBuildInfo(self, librarian, slave_status)
        return d.addCallback(self._reset_buildqueue_record)

    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger,
                                send_notification):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (self.buildqueue_record.specific_job.build.title,
                          self.buildqueue_record.builder.name))

        def build_info_stored(ignored):
            # XXX cprov 2006-05-30: Currently this information is not
            # properly presented in the Web UI. We will discuss it in
            # the next Paris Summit, infinity has some ideas about how
            # to use this content. For now we just ensure it's stored.
            d = self.buildqueue_record.builder.cleanSlave()
            self._reset_buildqueue_record()
            return d

        d = self.storeBuildInfo(self, librarian, slave_status)
        return d.addCallback(build_info_stored)


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
