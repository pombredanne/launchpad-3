# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build base classes."""

__metaclass__ = type

__all__ = ['BuildBase']

import datetime
import logging
import os
import subprocess
import time
import pytz

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.librarian.utils import copy_and_close
from lp.registry.interfaces.pocket import pocketsuffix
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache, cursor)

class BuildBase:
    def handleBuildStatus(self, status, queueItem, librarian, buildid,
                          filemap, dependencies):
        """Handle a finished build status.

        Different actions will be taken depending on the given status.
        """
        # XXX: queueItem should be gettable from self?
        logger = logging.getLogger()

        method = getattr(self, 'buildStatus_' + status, None)

        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, queueItem.builder.url))
            return

        method(queueItem, librarian, buildid, filemap, dependencies, logger)

    def buildStatus_OK(self, queueItem, librarian, buildid,
                       filemap=None, dependencies=None, logger=None):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        # XXX cprov 2007-07-11 bug=129487: untested code path.

        logger.debug("Processing successful build %s" % buildid)
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        if not build.archive.allowUpdatesToReleasePocket():
            assert build.distroseries.canUploadToPocket(build.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (build.title, build.id,
                   build.pocket.name))

        # ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)
        incoming = os.path.join(root, 'incoming')

        # create a single directory to store build result files
        # UPLOAD_LEAF: <TIMESTAMP>-<BUILD_ID>-<BUILDQUEUE_ID>
        upload_leaf = "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), buildid)
        upload_dir = os.path.join(incoming, upload_leaf)
        logger.debug("Storing build result at '%s'" % upload_dir)

        # Build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #       <archive_id>/distribution_name
        # for all destination archive types.
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        archive = build.archive
        distribution_name = build.distribution.name
        target_path = '%s/%s' % (archive.id, distribution_name)
        upload_path = os.path.join(upload_dir, target_path)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(queueItem.builder.slave)
        for filename in filemap:
            slave_file = slave.getFile(filemap[filename])
            out_file_name = os.path.join(upload_path, filename)
            out_file = open(out_file_name, "wb")
            copy_and_close(slave_file, out_file)

        uploader_argv = list(config.builddmaster.uploader.split())
        uploader_logfilename = os.path.join(upload_dir, 'uploader.log')
        logger.debug("Saving uploader log at '%s'"
                     % uploader_logfilename)

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" %  uploader_logfilename,
            "-d", "%s" % build.distribution.name,
            "-s", "%s" % (build.distroseries.name +
                          pocketsuffix[build.pocket]),
            "-b", "%s" % build.id,
            "-J", "%s" % upload_leaf,
            "%s" % root,
            ]

        uploader_argv.extend(extra_args)

        logger.debug("Invoking uploader on %s" % root)
        logger.debug("%s" % uploader_argv)

        uploader_process = subprocess.Popen(
            uploader_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Nothing should be written to the stdout/stderr.
        upload_stdout, upload_stderr = uploader_process.communicate()

        # XXX cprov 2007-04-17: we do not check uploader_result_code
        # anywhere. We need to find out what will be best strategy
        # when it failed HARD (there is a huge effort in process-upload
        # to not return error, it only happen when the code is broken).
        uploader_result_code = uploader_process.returncode
        logger.debug("Uploader returned %d" % uploader_result_code)

        # Quick and dirty hack to carry on on process-upload failures
        if os.path.exists(upload_dir):
            logger.debug("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            if not os.path.exists(failed_dir):
                os.mkdir(failed_dir)
            os.rename(upload_dir, os.path.join(failed_dir, upload_leaf))

        # The famous 'flush_updates + clear_cache' will make visible
        # the DB changes done in process-upload, considering that the
        # transaction was set with ISOLATION_LEVEL_READ_COMMITED
        # isolation level.
        cur = cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        assert isolation_str == 'read committed', (
            'BuildMaster/BuilderGroup transaction isolation should be '
            'ISOLATION_LEVEL_READ_COMMITTED (not "%s")' % isolation_str)

        original_slave = queueItem.builder.slave

        # XXX: Add XXX
        # XXX Robert Collins, Celso Providelo 2007-05-26:
        # 'Refreshing' objects  procedure  is forced on us by using a
        # different process to do the upload, but as that process runs
        # in the same unix account, it is simply double handling and we
        # would be better off to do it within this process.
        flush_database_updates()
        clear_current_connection_cache()

        # XXX cprov 2007-06-15: Re-issuing removeSecurityProxy is forced on
        # us by sqlobject refreshing the builder object during the
        # transaction cache clearing. Once we sort the previous problem
        # this step should probably not be required anymore.
        queueItem.builder.setSlaveForTesting(
            removeSecurityProxy(original_slave))

        # Store build information, build record was already updated during
        # the binary upload.
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)

        # Retrive the up-to-date build record and perform consistency
        # checks. The build record should be updated during the binary
        # upload processing, if it wasn't something is broken and needs
        # admins attention. Even when we have a FULLYBUILT build record,
        # if it is not related with at least one binary, there is also
        # a problem.
        # For both situations we will mark the builder as FAILEDTOUPLOAD
        # and the and update the build details (datebuilt, duration,
        # buildlog, builder) in LP. A build-failure-notification will be
        # sent to the lp-build-admin celebrity and to the sourcepackagerelease
        # uploader about this occurrence. The failure notification will
        # also contain the information required to manually reprocess the
        # binary upload when it was the case.
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        if (build.buildstate != BuildStatus.FULLYBUILT or
            build.binarypackages.count() == 0):
            logger.debug("Build %s upload failed." % build.id)
            build.buildstate = BuildStatus.FAILEDTOUPLOAD
            # Retrieve log file content.
            possible_locations = (
                'failed', 'failed-to-move', 'rejected', 'accepted')
            for location_dir in possible_locations:
                upload_final_location = os.path.join(
                    root, location_dir, upload_leaf)
                if os.path.exists(upload_final_location):
                    log_filepath = os.path.join(
                        upload_final_location, 'uploader.log')
                    uploader_log_file = open(log_filepath)
                    try:
                        uploader_log_content = uploader_log_file.read()
                    finally:
                        uploader_log_file.close()
                    break
            else:
                uploader_log_content = 'Could not find upload log file'
            # Store the upload_log_contents in librarian so it can be
            # accessed by anyone with permission to see the build.
            build.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            build.notify(extra_info=uploader_log_content)
        else:
            logger.debug(
                "Gathered build %s completely" %
                build.sourcepackagerelease.name)

        # Release the builder for another job.
        queueItem.builder.cleanSlave()
        # Remove BuildQueue record.
        queueItem.destroySelf()

    def buildStatus_PACKAGEFAIL(self, queueItem, librarian, buildid,
                                filemap=None, dependencies=None, logger=None):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        build.buildstate = BuildStatus.FAILEDTOBUILD
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        queueItem.builder.cleanSlave()
        build.notify()
        queueItem.destroySelf()

    def buildStatus_DEPFAIL(self, queueItem, librarian, buildid,
                            filemap=None, dependencies=None, logger=None):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        build.buildstate = BuildStatus.MANUALDEPWAIT
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        logger.critical("***** %s is MANUALDEPWAIT *****"
                        % queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.destroySelf()

    def buildStatus_CHROOTFAIL(self, queueItem, librarian, buildid,
                               filemap=None, dependencies=None, logger=None):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        build.buildstate = BuildStatus.CHROOTWAIT
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        logger.critical("***** %s is CHROOTWAIT *****" %
                        queueItem.builder.name)
        queueItem.builder.cleanSlave()
        build.notify()
        queueItem.destroySelf()

    def buildStatus_BUILDERFAIL(self, queueItem, librarian, buildid,
                                filemap=None, dependencies=None, logger=None):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % queueItem.builder.name)
        queueItem.builder.failbuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        # simply reset job
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        queueItem.reset()

    def buildStatus_GIVENBACK(self, queueItem, librarian, buildid,
                              filemap=None, dependencies=None, logger=None):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (buildid, queueItem.builder.name))
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        queueItem.builder.cleanSlave()
        queueItem.reset()

    def getLogFromSlave(self, queueItem):
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        return queueItem.builder.transferSlaveFileToLibrarian(
            'buildlog', queueItem.getLogFileName(),
            build.archive.private)

    def storeBuildInfo(self, queueItem, librarian, buildid, dependencies):
        """Store available information for build jobs.

        Store Buildlog, datebuilt, duration, dependencies.
        """
        build = getUtility(IBuildSet).getByQueueEntry(queueItem)
        build.buildlog = self.getLogFromSlave(queueItem)
        build.builder = queueItem.builder
        build.dependencies = dependencies
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        build.datebuilt = UTC_NOW
        # We need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        build.buildduration = RIGHT_NOW - queueItem.date_started
