# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build base classes."""

__metaclass__ = type

__all__ = ['BuildBase']

import datetime
import logging
import os
import pytz
import subprocess
import time

from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    clear_current_connection_cache, cursor, flush_database_updates)
from canonical.librarian.utils import copy_and_close
from lp.registry.interfaces.pocket import pocketsuffix
from lp.soyuz.interfaces.build import BuildStatus


class BuildBase:

    # XXX: Add a method to be overridden to specify policy to use.

    def handleStatus(self, status, librarian, slave_status):
        """See `IBuildBase`."""
        logger = logging.getLogger()

        method = getattr(self, '_handleStatus_' + status, None)

        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, self.buildqueue_record.builder.url))
            return

        method(librarian, slave_status, logger)

    def _handleStatus_OK(self, librarian, slave_status, logger):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        # XXX cprov 2007-07-11 bug=129487: untested code path.
        buildid = slave_status['build_id']
        filemap = slave_status['filemap']

        logger.debug("Processing successful build %s" % buildid)
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distroseries.canUploadToPocket(self.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (self.title, self.id, self.pocket.name))

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
        archive = self.archive
        distribution_name = self.distribution.name
        target_path = '%s/%s' % (archive.id, distribution_name)
        upload_path = os.path.join(upload_dir, target_path)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(self.buildqueue_record.builder.slave)
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

        # XXX: Pass the policy in here, rather than in the config.
        extra_args = [
            "--log-file", "%s" %  uploader_logfilename,
            "-d", "%s" % self.distribution.name,
            "-s", "%s" % (self.distroseries.name +
                          pocketsuffix[self.pocket]),
            "-b", "%s" % self.id,
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

        original_slave = self.buildqueue_record.builder.slave

        # XXX Robert Collins, Celso Providelo 2007-05-26 bug=506256:
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
        self.buildqueue_record.builder.setSlaveForTesting(
            removeSecurityProxy(original_slave))

        # Store build information, build record was already updated during
        # the binary upload.
        self.storeBuildInfo(librarian, slave_status)

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
        if (self.buildstate != BuildStatus.FULLYBUILT or
            self.binarypackages.count() == 0):
            logger.debug("Build %s upload failed." % self.id)
            self.buildstate = BuildStatus.FAILEDTOUPLOAD
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
            self.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            self.notify(extra_info=uploader_log_content)
        else:
            logger.debug(
                "Gathered build %s completely" %
                self.sourcepackagerelease.name)

        # Release the builder for another job.
        self.buildqueue_record.builder.cleanSlave()
        # Remove BuildQueue record.
        self.buildqueue_record.destroySelf()

    def _handleStatus_PACKAGEFAIL(self, librarian, slave_status, logger):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        self.buildstate = BuildStatus.FAILEDTOBUILD
        self.storeBuildInfo(librarian, slave_status)
        self.buildqueue_record.builder.cleanSlave()
        self.notify()
        self.buildqueue_record.destroySelf()

    def _handleStatus_DEPFAIL(self, librarian, slave_status, logger):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        self.buildstate = BuildStatus.MANUALDEPWAIT
        self.storeBuildInfo(librarian, slave_status)
        logger.critical("***** %s is MANUALDEPWAIT *****"
                        % self.buildqueue_record.builder.name)
        self.buildqueue_record.builder.cleanSlave()
        self.buildqueue_record.destroySelf()

    def _handleStatus_CHROOTFAIL(self, librarian, slave_status,
                                 logger):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        self.buildstate = BuildStatus.CHROOTWAIT
        self.storeBuildInfo(librarian, slave_status)
        logger.critical("***** %s is CHROOTWAIT *****" %
                        self.buildqueue_record.builder.name)
        self.buildqueue_record.builder.cleanSlave()
        self.notify()
        self.buildqueue_record.destroySelf()

    def _handleStatus_BUILDERFAIL(self, librarian, slave_status, logger):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % self.buildqueue_record.builder.name)
        self.buildqueue_record.builder.failBuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        # simply reset job
        self.storeBuildInfo(librarian, slave_status)
        self.buildqueue_record.reset()

    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (slave_status['build_id'],
                          self.buildqueue_record.builder.name))
        self.storeBuildInfo(librarian, slave_status)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        self.buildqueue_record.builder.cleanSlave()
        self.buildqueue_record.reset()

    def getLogFromSlave(self):
        """See `IBuildBase`."""
        return self.buildqueue_record.builder.transferSlaveFileToLibrarian(
            'buildlog', self.buildqueue_record.getLogFileName(),
            self.is_private)

    def storeBuildInfo(self, librarian, slave_status):
        """See `IBuildBase`."""
        self.buildlog = self.getLogFromSlave()
        self.builder = self.buildqueue_record.builder
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        self.datebuilt = UTC_NOW
        # We need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        self.buildduration = RIGHT_NOW - self.buildqueue_record.date_started
        self.dependencies = slave_status.get('dependencies')

