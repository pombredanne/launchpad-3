# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Base and idle BuildFarmJobBehavior classes."""

__metaclass__ = type

__all__ = [
    'BuildFarmJobBehaviorBase',
    'IdleBuildBehavior',
    ]

import datetime
import logging
import os.path

import transaction
from twisted.internet import defer
from zope.interface import implements

from lp.buildmaster.enums import (
    BuildFarmJobType,
    BuildStatus,
    )
from lp.buildmaster.interfaces.builder import (
    BuildSlaveFailure,
    CorruptBuildCookie,
    )
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch,
    IBuildFarmJobBehavior,
    )
from lp.services.config import config


SLAVE_LOG_FILENAME = 'buildlog'


class BuildFarmJobBehaviorBase:
    """Ensures that all behaviors inherit the same initialization.

    All build-farm job behaviors should inherit from this.
    """

    def __init__(self, buildfarmjob):
        """Store a reference to the job_type with which we were created."""
        self.buildfarmjob = buildfarmjob
        self._builder = None

    @property
    def build(self):
        return self.buildfarmjob.build

    def setBuilderInteractor(self, interactor):
        """The builder should be set once and not changed."""
        self._interactor = interactor
        self._builder = interactor.builder

    def verifyBuildRequest(self, logger):
        """The default behavior is a no-op."""
        pass

    def updateSlaveStatus(self, raw_slave_status, status):
        """See `IBuildFarmJobBehavior`.

        The default behavior is that we don't add any extra values."""
        pass

    def verifySlaveBuildCookie(self, slave_build_cookie):
        """See `IBuildFarmJobBehavior`."""
        expected_cookie = self.buildfarmjob.generateSlaveBuildCookie()
        if slave_build_cookie != expected_cookie:
            raise CorruptBuildCookie("Invalid slave build cookie.")

    def getBuildCookie(self):
        """See `IPackageBuild`."""
        return '%s-%s' % (self.build.job_type.name, self.build.id)

    def getUploadDirLeaf(self, build_cookie, now=None):
        """See `IPackageBuild`."""
        if now is None:
            now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d-%H%M%S")
        return '%s-%s' % (timestamp, build_cookie)

    def getLogFromSlave(self, queue_item):
        """See `IPackageBuild`."""
        d = self._interactor.transferSlaveFileToLibrarian(
            SLAVE_LOG_FILENAME, queue_item.getLogFileName(),
            self.build.is_private)
        return d

    @defer.inlineCallbacks
    def storeLogFromSlave(self, build_queue=None):
        """See `IBuildFarmJob`."""
        lfa_id = yield self.getLogFromSlave(
            build_queue or self.build.buildqueue_record)
        self.build.setLog(lfa_id)
        transaction.commit()

    # The list of build status values for which email notifications are
    # allowed to be sent. It is up to each callback as to whether it will
    # consider sending a notification but it won't do so if the status is not
    # in this list.
    ALLOWED_STATUS_NOTIFICATIONS = ['OK', 'PACKAGEFAIL', 'CHROOTFAIL']

    def handleStatus(self, status, librarian, slave_status):
        """See `IBuildFarmJobBehavior`."""
        from lp.buildmaster.manager import BUILDD_MANAGER_LOG_NAME
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)
        send_notification = status in self.ALLOWED_STATUS_NOTIFICATIONS
        method = getattr(self, '_handleStatus_' + status, None)
        if method is None:
            logger.critical(
                "Unknown BuildStatus '%s' for builder '%s'"
                % (status, self.build.buildqueue_record.builder.url))
            return
        logger.info(
            'Processing finished %s build %s (%s) from builder %s'
            % (status, self.getBuildCookie(),
               self.build.buildqueue_record.specific_job.build.title,
               self.build.buildqueue_record.builder.name))
        d = method(librarian, slave_status, logger, send_notification)
        return d

    @defer.inlineCallbacks
    def _handleStatus_OK(self, librarian, slave_status, logger,
                         send_notification):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        build = self.build
        filemap = slave_status['filemap']

        # If this is a binary package build, discard it if its source is
        # no longer published.
        if build.job_type == BuildFarmJobType.PACKAGEBUILD:
            build = build.buildqueue_record.specific_job.build
            if not build.current_source_publication:
                yield self._interactor.cleanSlave()
                build.updateStatus(BuildStatus.SUPERSEDED)
                self.build.buildqueue_record.destroySelf()
                return

        # Explode before collect a binary that is denied in this
        # distroseries/pocket/archive
        assert build.archive.canModifySuite(
            build.distro_series, build.pocket), (
                "%s (%s) can not be built for pocket %s in %s: illegal status"
                % (build.title, build.id, build.pocket.name, build.archive))

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
            grab_dir, str(build.archive.id), build.distribution.name)
        os.makedirs(upload_path)

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
                    "for the build %d." % (filename, build.id))
                break
            filenames_to_download[filemap[filename]] = out_file_name
        yield self._interactor.slave.getFiles(filenames_to_download)

        status = (
            BuildStatus.UPLOADING if successful_copy_from_slave
            else BuildStatus.FAILEDTOUPLOAD)
        # XXX wgrant: The builder should be set long before here, but
        # currently isn't.
        build.updateStatus(
            status, builder=build.buildqueue_record.builder,
            slave_status=slave_status)
        transaction.commit()

        yield self.storeLogFromSlave()

        # We only attempt the upload if we successfully copied all the
        # files from the slave.
        if successful_copy_from_slave:
            logger.info(
                "Gathered %s %d completely. Moving %s to uploader queue."
                % (build.__class__.__name__, build.id, upload_leaf))
            target_dir = os.path.join(root, "incoming")
        else:
            logger.warning(
                "Copy from slave for build %s was unsuccessful.", build.id)
            if send_notification:
                build.notify(
                    extra_info='Copy from slave was unsuccessful.')
            target_dir = os.path.join(root, "failed")

        if not os.path.exists(target_dir):
            os.mkdir(target_dir)

        yield self._interactor.cleanSlave()
        self.build.buildqueue_record.destroySelf()
        transaction.commit()

        # Move the directory used to grab the binaries into
        # the incoming directory so the upload processor never
        # sees half-finished uploads.
        os.rename(grab_dir, os.path.join(target_dir, upload_leaf))

    @defer.inlineCallbacks
    def _handleStatus_generic_failure(self, status, librarian, slave_status,
                                      logger, send_notification):
        """Handle a generic build failure.

        The build, not the builder, has failed. Set its status, store
        available information, and remove the queue entry.
        """
        # XXX wgrant: The builder should be set long before here, but
        # currently isn't.
        self.build.updateStatus(
            status, builder=self.build.buildqueue_record.builder,
            slave_status=slave_status)
        transaction.commit()
        yield self.storeLogFromSlave()
        if send_notification:
            self.build.notify()
        yield self._interactor.cleanSlave()
        self.build.buildqueue_record.destroySelf()
        transaction.commit()

    def _handleStatus_PACKAGEFAIL(self, librarian, slave_status, logger,
                                  send_notification):
        """Handle a package that had failed to build."""
        return self._handleStatus_generic_failure(
            BuildStatus.FAILEDTOBUILD, librarian, slave_status, logger,
            send_notification)

    def _handleStatus_DEPFAIL(self, librarian, slave_status, logger,
                              send_notification):
        """Handle a package that had missing dependencies."""
        return self._handleStatus_generic_failure(
            BuildStatus.MANUALDEPWAIT, librarian, slave_status, logger,
            send_notification)

    def _handleStatus_CHROOTFAIL(self, librarian, slave_status, logger,
                                 send_notification):
        """Handle a package that had failed when unpacking the CHROOT."""
        return self._handleStatus_generic_failure(
            BuildStatus.CHROOTWAIT, librarian, slave_status, logger,
            send_notification)

    def _handleStatus_BUILDERFAIL(self, librarian, slave_status, logger,
                                  send_notification):
        """Handle builder failures.

        Fail the builder, and reset the job.
        """
        self.build.buildqueue_record.builder.failBuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        self.build.buildqueue_record.reset()
        transaction.commit()

    @defer.inlineCallbacks
    def _handleStatus_ABORTED(self, librarian, slave_status, logger,
                              send_notification):
        """Handle aborted builds.

        If the build was explicitly cancelled, then mark it as such.
        Otherwise, the build has failed in some unexpected way.
        """
        if self.build.status == BuildStatus.CANCELLING:
            self.build.buildqueue_record.cancel()
            transaction.commit()
            yield self._interactor.cleanSlave()
        else:
            self.build.buildqueue_record.reset()
            try:
                self._builder.handleFailure(logger)
                yield self._interactor.resetOrFail(
                    logger,
                    BuildSlaveFailure("Builder unexpectedly returned ABORTED"))
            except Exception as e:
                # We've already done our best to mark the builder as failed.
                logger.error("Failed to rescue from ABORTED: %s" % e)
        transaction.commit()

    @defer.inlineCallbacks
    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger,
                                send_notification):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        yield self._interactor.cleanSlave()
        self.build.buildqueue_record.reset()
        transaction.commit()


class IdleBuildBehavior(BuildFarmJobBehaviorBase):

    implements(IBuildFarmJobBehavior)

    def __init__(self):
        """The idle behavior is special in that a buildfarmjob is not
        specified during initialization as it is not the result of an
        adaption.
        """
        super(IdleBuildBehavior, self).__init__(None)

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to log the start of a build.")

    def dispatchBuildToSlave(self, build_queue_item_id, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to dispatch a build to the slave.")

    @property
    def status(self):
        """See `IBuildFarmJobBehavior`."""
        return "Idle"

    def verifySlaveBuildCookie(self, slave_build_id):
        """See `IBuildFarmJobBehavior`."""
        raise CorruptBuildCookie('No job assigned to builder')
