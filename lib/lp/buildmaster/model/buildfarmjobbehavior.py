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
import socket
import xmlrpclib

from storm.store import Store
from twisted.internet import defer
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

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
from lp.services import encoding
from lp.services.config import config
from lp.services.job.interfaces.job import JobStatus
from lp.services.librarian.interfaces.client import ILibrarianClient


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

    def setBuilder(self, builder):
        """The builder should be set once and not changed."""
        self._builder = builder

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

    @staticmethod
    def getLogFromSlave(build, queue_item):
        """See `IPackageBuild`."""
        d = queue_item.builder.transferSlaveFileToLibrarian(
            SLAVE_LOG_FILENAME, queue_item.getLogFileName(),
            build.is_private)
        return d

    @defer.inlineCallbacks
    def storeLogFromSlave(self):
        """See `IBuildFarmJob`."""
        lfa_id = yield self.getLogFromSlave(
            self.build, self.build.buildqueue_record)
        self.build.setLog(lfa_id)

    def updateBuild(self, queueItem):
        """See `IBuildFarmJobBehavior`."""
        logger = logging.getLogger('slave-scanner')

        d = self._builder.slaveStatus()

        def got_failure(failure):
            failure.trap(xmlrpclib.Fault, socket.error)
            info = failure.value
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            raise BuildSlaveFailure(info)

        def got_status(slave_status):
            builder_status_handlers = {
                'BuilderStatus.IDLE': self.updateBuild_IDLE,
                'BuilderStatus.BUILDING': self.updateBuild_BUILDING,
                'BuilderStatus.ABORTING': self.updateBuild_ABORTING,
                'BuilderStatus.ABORTED': self.updateBuild_ABORTED,
                'BuilderStatus.WAITING': self.updateBuild_WAITING,
                }

            builder_status = slave_status['builder_status']
            if builder_status not in builder_status_handlers:
                logger.critical(
                    "Builder on %s returned unknown status %s, failing it"
                    % (self._builder.url, builder_status))
                self._builder.failBuilder(
                    "Unknown status code (%s) returned from status() probe."
                    % builder_status)
                # XXX: This will leave the build and job in a bad state, but
                # should never be possible, since our builder statuses are
                # known.
                queueItem._builder = None
                queueItem.setDateStarted(None)
                return

            # Since logtail is a xmlrpclib.Binary container and it is
            # returned from the IBuilder content class, it arrives
            # protected by a Zope Security Proxy, which is not declared,
            # thus empty. Before passing it to the status handlers we
            # will simply remove the proxy.
            logtail = removeSecurityProxy(slave_status.get('logtail'))

            method = builder_status_handlers[builder_status]
            return defer.maybeDeferred(
                method, queueItem, slave_status, logtail, logger)

        d.addErrback(got_failure)
        d.addCallback(got_status)
        return d

    def updateBuild_IDLE(self, queueItem, slave_status, logtail, logger):
        """Somehow the builder forgot about the build job.

        Log this and reset the record.
        """
        logger.warn(
            "Builder %s forgot about buildqueue %d -- resetting buildqueue "
            "record" % (queueItem.builder.url, queueItem.id))
        queueItem.reset()

    def updateBuild_BUILDING(self, queueItem, slave_status, logtail, logger):
        """Build still building, collect the logtail"""
        if queueItem.job.status != JobStatus.RUNNING:
            queueItem.job.start()
        queueItem.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, queueItem, slave_status, logtail, logger):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """
        queueItem.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, queueItem, slave_status, logtail, logger):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """
        d = queueItem.builder.cleanSlave()

        def got_cleaned(ignored):
            queueItem.builder = None
            if queueItem.job.status != JobStatus.FAILED:
                queueItem.job.fail()
            queueItem.specific_job.jobAborted()
        return d.addCallback(got_cleaned)

    def extractBuildStatus(self, slave_status):
        """Read build status name.

        :param slave_status: build status dict as passed to the
            updateBuild_* methods.
        :return: the unqualified status name, e.g. "OK".
        """
        status_string = slave_status['build_status']
        lead_string = 'BuildStatus.'
        assert status_string.startswith(lead_string), (
            "Malformed status string: '%s'" % status_string)

        return status_string[len(lead_string):]

    def updateBuild_WAITING(self, queueItem, slave_status, logtail, logger):
        """Perform the actions needed for a slave in a WAITING state

        Buildslave can be WAITING in five situations:

        * Build has failed, no filemap is received (PACKAGEFAIL, DEPFAIL,
                                                    CHROOTFAIL, BUILDERFAIL)

        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrieve those files and store in
          Librarian with getFileFromSlave() and then pass the binaries to
          the uploader for processing.
        """
        librarian = getUtility(ILibrarianClient)
        build_status = self.extractBuildStatus(slave_status)

        # XXX: dsilvers 2005-03-02: Confirm the builder has the right build?
        d = self.handleStatus(build_status, librarian, slave_status)
        return d

    # The list of build status values for which email notifications are
    # allowed to be sent. It is up to each callback as to whether it will
    # consider sending a notification but it won't do so if the status is not
    # in this list.
    ALLOWED_STATUS_NOTIFICATIONS = ['OK', 'PACKAGEFAIL', 'CHROOTFAIL']

    def handleStatus(self, status, librarian, slave_status):
        """See `IPackageBuild`."""
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
        if build.build_farm_job_type == BuildFarmJobType.PACKAGEBUILD:
            build = build.buildqueue_record.specific_job.build
            if not build.current_source_publication:
                build.updateStatus(BuildStatus.SUPERSEDED)
                yield self.build.buildqueue_record.builder.cleanSlave()
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

        slave = removeSecurityProxy(build.buildqueue_record.builder.slave)
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
        yield slave.getFiles(filenames_to_download)

        status = (
            BuildStatus.UPLOADING if successful_copy_from_slave
            else BuildStatus.FAILEDTOUPLOAD)
        # XXX wgrant: The builder should be set long before here, but
        # currently isn't.
        build.updateStatus(
            status, builder=build.buildqueue_record.builder,
            slave_status=slave_status)
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

        yield self.build.buildqueue_record.builder.cleanSlave()
        self.build.buildqueue_record.destroySelf()

        # Commit so there are no race conditions with archiveuploader
        # about build.status.
        Store.of(build).commit()

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
        yield self.storeLogFromSlave()
        if send_notification:
            self.build.notify()
        yield self.build.buildqueue_record.builder.cleanSlave()
        self.build.buildqueue_record.destroySelf()

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

    @defer.inlineCallbacks
    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger,
                                send_notification):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        yield self.build.buildqueue_record.builder.cleanSlave()
        self.build.buildqueue_record.reset()


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
