# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

from __future__ import with_statement

"""Common build base classes."""

__metaclass__ = type

__all__ = ['BuildBase']

import datetime
import logging
import os
import pytz
import subprocess
from cStringIO import StringIO

from storm.store import Store
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    clear_current_connection_cache, cursor, flush_database_updates)
from canonical.launchpad.helpers import filenameToContentType
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.librarian.utils import copy_and_close
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.buildmaster.interfaces.buildbase import BUILDD_MANAGER_LOG_NAME
from lp.registry.interfaces.pocket import pocketsuffix


UPLOAD_LOG_FILENAME = 'uploader.log'


class BuildBase:
    """A mixin class providing functionality for farm jobs that build a
    package.

    Note: this class does not implement IBuildBase as we currently duplicate
    the properties defined on IBuildBase on the inheriting class tables.
    BuildBase cannot therefore implement IBuildBase itself, as storm requires
    that the corresponding __storm_table__ be defined for the class. Instead,
    the classes using the BuildBase mixin must ensure that they implement IBuildBase.
    """
    policy_name = 'buildd'

    @staticmethod
    def getUploadLeaf(build_id, now=None):
        """Return a directory name to store build things in.

        :param build_id: The id as returned by the slave, normally
            $BUILD_ID-$BUILDQUEUE_ID
        :param now: The `datetime` to use. If not provided, defaults to now.
        """
        # UPLOAD_LEAF: <TIMESTAMP>-<BUILD_ID>-<BUILDQUEUE_ID>
        if now is None:
            now = datetime.datetime.now()
        return '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_id)

    @staticmethod
    def getUploadDir(upload_leaf):
        """Return the directory that things will be stored in."""
        return os.path.join(config.builddmaster.root, 'incoming', upload_leaf)

    @staticmethod
    def getUploaderCommand(package_build, distroseries, upload_leaf,
                           uploader_logfilename):
        """See `IBuildBase`."""
        root = os.path.abspath(config.builddmaster.root)
        uploader_command = list(config.builddmaster.uploader.split())

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" % uploader_logfilename,
            "-d", "%s" % distroseries.distribution.name,
            "-s", "%s" % (distroseries.name +
                          pocketsuffix[package_build.pocket]),
            "-b", "%s" % package_build.id,
            "-J", "%s" % upload_leaf,
            '--context=%s' % package_build.policy_name,
            "%s" % root,
            ]

        uploader_command.extend(extra_args)
        return uploader_command

    def _getProxiedFileURL(self, library_file):
        """Return the 'http_url' of a `ProxiedLibraryFileAlias`."""
        # Avoiding circular imports.
        from canonical.launchpad.browser.librarian import (
            ProxiedLibraryFileAlias)

        proxied_file = ProxiedLibraryFileAlias(library_file, self)
        return proxied_file.http_url

    @property
    def build_log_url(self):
        """See `IBuildBase`."""
        if self.buildlog is None:
            return None
        return self._getProxiedFileURL(self.buildlog)

    @staticmethod
    def getUploadLogContent(root, leaf):
        """Retrieve the upload log contents.

        :param root: Root directory for the uploads
        :param leaf: Leaf for this particular upload
        :return: Contents of log file or message saying no log file was found.
        """
        # Retrieve log file content.
        possible_locations = (
            'failed', 'failed-to-move', 'rejected', 'accepted')
        for location_dir in possible_locations:
            log_filepath = os.path.join(root, location_dir, leaf,
                UPLOAD_LOG_FILENAME)
            if os.path.exists(log_filepath):
                with open(log_filepath, 'r') as uploader_log_file:
                    return uploader_log_file.read()
        else:
            return 'Could not find upload log file'

    @property
    def upload_log_url(self):
        """See `IBuildBase`."""
        if self.upload_log is None:
            return None
        return self._getProxiedFileURL(self.upload_log)

    def handleStatus(self, status, librarian, slave_status):
        """See `IBuildBase`."""
        logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)

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
        filemap = slave_status['filemap']

        logger.info("Processing successful build %s from builder %s" % (
            self.buildqueue_record.specific_job.build.title,
            self.buildqueue_record.builder.name))
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not self.archive.allowUpdatesToReleasePocket():
            assert self.distroseries.canUploadToPocket(self.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (self.title, self.id, self.pocket.name))

        # ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)

        # create a single directory to store build result files
        upload_leaf = self.getUploadLeaf(
            '%s-%s' % (self.id, self.buildqueue_record.id))
        upload_dir = self.getUploadDir(upload_leaf)
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
        successful_copy_from_slave = True
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
            out_file = open(out_file_name, "wb")
            slave_file = slave.getFile(filemap[filename])
            copy_and_close(slave_file, out_file)

        # We only attempt the upload if we successfully copied all the
        # files from the slave.
        if successful_copy_from_slave:
            uploader_logfilename = os.path.join(
                upload_dir, UPLOAD_LOG_FILENAME)
            uploader_command = self.getUploaderCommand(
                self, self.distroseries, upload_leaf, uploader_logfilename)
            logger.debug("Saving uploader log at '%s'" % uploader_logfilename)

            logger.info("Invoking uploader on %s" % root)
            logger.info("%s" % uploader_command)

            uploader_process = subprocess.Popen(
                uploader_command, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

            # Nothing should be written to the stdout/stderr.
            upload_stdout, upload_stderr = uploader_process.communicate()

            # XXX cprov 2007-04-17: we do not check uploader_result_code
            # anywhere. We need to find out what will be best strategy
            # when it failed HARD (there is a huge effort in process-upload
            # to not return error, it only happen when the code is broken).
            uploader_result_code = uploader_process.returncode
            logger.info("Uploader returned %d" % uploader_result_code)

        # Quick and dirty hack to carry on on process-upload failures
        if os.path.exists(upload_dir):
            logger.warning("The upload directory did not get moved.")
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
        self.storeBuildInfo(self, librarian, slave_status)

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
            not successful_copy_from_slave or
            not self.verifySuccessfulUpload()):
            logger.warning("Build %s upload failed." % self.id)
            self.buildstate = BuildStatus.FAILEDTOUPLOAD
            uploader_log_content = self.getUploadLogContent(root,
                upload_leaf)
            # Store the upload_log_contents in librarian so it can be
            # accessed by anyone with permission to see the build.
            self.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            self.notify(extra_info=uploader_log_content)
        else:
            logger.info(
                "Gathered %s %d completely" % (
                self.__class__.__name__, self.id))

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
        self.storeBuildInfo(self, librarian, slave_status)
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
        self.storeBuildInfo(self, librarian, slave_status)
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
        self.storeBuildInfo(self, librarian, slave_status)
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
        self.storeBuildInfo(self, librarian, slave_status)
        self.buildqueue_record.reset()

    def _handleStatus_GIVENBACK(self, librarian, slave_status, logger):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (self.buildqueue_record.specific_job.build.title,
                          self.buildqueue_record.builder.name))
        self.storeBuildInfo(self, librarian, slave_status)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        self.buildqueue_record.builder.cleanSlave()
        self.buildqueue_record.reset()

    @staticmethod
    def getLogFromSlave(build):
        """See `IBuildBase`."""
        return build.buildqueue_record.builder.transferSlaveFileToLibrarian(
            'buildlog', build.buildqueue_record.getLogFileName(),
            build.is_private)

    @staticmethod
    def storeBuildInfo(build, librarian, slave_status):
        """See `IBuildBase`."""
        build.buildlog = build.getLogFromSlave(build)
        build.builder = build.buildqueue_record.builder
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        build.datebuilt = UTC_NOW
        # We need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        build.buildduration = RIGHT_NOW - build.buildqueue_record.date_started
        if slave_status.get('dependencies') is not None:
            build.dependencies = unicode(slave_status.get('dependencies'))
        else:
            build.dependencies = None

    @staticmethod
    def createUploadLog(build, content, filename=None):
        """Creates a file on the librarian for the upload log.

        :return: ILibraryFileAlias for the upload log file.
        """
        # The given content is stored in the librarian, restricted as
        # necessary according to the targeted archive's privacy.  The content
        # object's 'upload_log' attribute will point to the
        # `LibrarianFileAlias`.

        assert build.upload_log is None, (
            "Upload log information already exists and cannot be overridden.")

        if filename is None:
            filename = 'upload_%s_log.txt' % build.id
        contentType = filenameToContentType(filename)
        file_size = len(content)
        file_content = StringIO(content)
        restricted = build.is_private

        return getUtility(ILibraryFileAliasSet).create(
            filename, file_size, file_content, contentType=contentType,
            restricted=restricted)

    def storeUploadLog(self, content):
        """See `IBuildBase`."""
        library_file = self.createUploadLog(self, content)
        self.upload_log = library_file

    def queueBuild(self, suspended=False):
        """See `IBuildBase`"""
        specific_job = self.makeJob()

        # This build queue job is to be created in a suspended state.
        if suspended:
            specific_job.job.suspend()

        duration_estimate = self.estimateDuration()
        queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=self.build_farm_job_type,
            job=specific_job.job, processor=specific_job.processor,
            virtualized=specific_job.virtualized)
        Store.of(self).add(queue_entry)
        return queue_entry

