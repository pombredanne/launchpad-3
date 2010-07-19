# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213


"""Common build base classes."""


from __future__ import with_statement

__metaclass__ = type

__all__ = [
    'handle_status_for_build',
    'BuildBase',
    ]

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


def handle_status_for_build(build, status, librarian, slave_status,
                            build_class=None):
    """Find and call the correct method for handling the build status.

    This is extracted from build base so that the implementation
    can be shared by the newer IPackageBuild class.
    """
    logger = logging.getLogger(BUILDD_MANAGER_LOG_NAME)

    if build_class is None:
        build_class = BuildBase
    method = getattr(build_class, '_handleStatus_' + status, None)

    if method is None:
        logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                        % (status, build.buildqueue_record.builder.url))
        return

    method(build, librarian, slave_status, logger)


class BuildBase:
    """A mixin class providing functionality for farm jobs that build a
    package.

    Note: this class does not implement IBuildBase as we currently duplicate
    the properties defined on IBuildBase on the inheriting class tables.
    BuildBase cannot therefore implement IBuildBase itself, as storm requires
    that the corresponding __storm_table__ be defined for the class. Instead,
    the classes using the BuildBase mixin must ensure that they implement
    IBuildBase.
    """
    policy_name = 'buildd'

    @staticmethod
    def getUploadDirLeaf(build_cookie, now=None):
        """See `IPackageBuild`."""
        # UPLOAD_LEAF: <TIMESTAMP>-<BUILD-COOKIE>
        if now is None:
            now = datetime.datetime.now()
        return '%s-%s' % (now.strftime("%Y%m%d-%H%M%S"), build_cookie)

    @staticmethod
    def getUploadDir(upload_leaf):
        """Return the directory that things will be stored in."""
        return os.path.join(config.builddmaster.root, 'incoming', upload_leaf)

    @staticmethod
    def getUploaderCommand(build, upload_leaf, uploader_logfilename):
        """See `IBuildBase`."""
        root = os.path.abspath(config.builddmaster.root)
        uploader_command = list(config.builddmaster.uploader.split())

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" % uploader_logfilename,
            "-d", "%s" % build.distribution.name,
            "-s", "%s" % (build.distro_series.name +
                          pocketsuffix[build.pocket]),
            "-b", "%s" % build.id,
            "-J", "%s" % upload_leaf,
            '--context=%s' % build.policy_name,
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
        return handle_status_for_build(
            self, status, librarian, slave_status, self.__class__)

    @staticmethod
    def _handleStatus_OK(build, librarian, slave_status, logger):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        filemap = slave_status['filemap']

        logger.info("Processing successful build %s from builder %s" % (
            build.buildqueue_record.specific_job.build.title,
            build.buildqueue_record.builder.name))
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        if not build.archive.allowUpdatesToReleasePocket():
            assert build.distro_series.canUploadToPocket(build.pocket), (
                "%s (%s) can not be built for pocket %s: illegal status"
                % (build.title, build.id, build.pocket.name))

        # ensure we have the correct build root as:
        # <BUILDMASTER_ROOT>/incoming/<UPLOAD_LEAF>/<TARGET_PATH>/[FILES]
        root = os.path.abspath(config.builddmaster.root)

        # create a single directory to store build result files
        upload_leaf = build.getUploadDirLeaf(
            '%s-%s' % (build.id, build.buildqueue_record.id))
        upload_dir = build.getUploadDir(upload_leaf)
        logger.debug("Storing build result at '%s'" % upload_dir)

        # Build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #       <archive_id>/distribution_name
        # for all destination archive types.
        archive = build.archive
        distribution_name = build.distribution.name
        target_path = '%s/%s' % (archive.id, distribution_name)
        upload_path = os.path.join(upload_dir, target_path)
        os.makedirs(upload_path)

        slave = removeSecurityProxy(build.buildqueue_record.builder.slave)
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
                    "for the build %d." % (filename, build.id))
                break
            out_file = open(out_file_name, "wb")
            slave_file = slave.getFile(filemap[filename])
            copy_and_close(slave_file, out_file)

        # We only attempt the upload if we successfully copied all the
        # files from the slave.
        if successful_copy_from_slave:
            uploader_logfilename = os.path.join(
                upload_dir, UPLOAD_LOG_FILENAME)
            uploader_command = build.getUploaderCommand(
                build, upload_leaf, uploader_logfilename)
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

        original_slave = build.buildqueue_record.builder.slave

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
        build.buildqueue_record.builder.setSlaveForTesting(
            removeSecurityProxy(original_slave))

        # Store build information, build record was already updated during
        # the binary upload.
        build.storeBuildInfo(build, librarian, slave_status)

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
        if (build.status != BuildStatus.FULLYBUILT or
            not successful_copy_from_slave or
            not build.verifySuccessfulUpload()):
            logger.warning("Build %s upload failed." % build.id)
            build.status = BuildStatus.FAILEDTOUPLOAD
            uploader_log_content = build.getUploadLogContent(root,
                upload_leaf)
            # Store the upload_log_contents in librarian so it can be
            # accessed by anyone with permission to see the build.
            build.storeUploadLog(uploader_log_content)
            # Notify the build failure.
            build.notify(extra_info=uploader_log_content)
        else:
            logger.info(
                "Gathered %s %d completely" % (
                build.__class__.__name__, build.id))

        # Release the builder for another job.
        build.buildqueue_record.builder.cleanSlave()
        # Remove BuildQueue record.
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_PACKAGEFAIL(build, librarian, slave_status, logger):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        build.status = BuildStatus.FAILEDTOBUILD
        build.storeBuildInfo(build, librarian, slave_status)
        build.buildqueue_record.builder.cleanSlave()
        build.notify()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_DEPFAIL(build, librarian, slave_status, logger):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        build.status = BuildStatus.MANUALDEPWAIT
        build.storeBuildInfo(build, librarian, slave_status)
        logger.critical("***** %s is MANUALDEPWAIT *****"
                        % build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.cleanSlave()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_CHROOTFAIL(build, librarian, slave_status,
                                 logger):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        build.status = BuildStatus.CHROOTWAIT
        build.storeBuildInfo(build, librarian, slave_status)
        logger.critical("***** %s is CHROOTWAIT *****" %
                        build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.cleanSlave()
        build.notify()
        build.buildqueue_record.destroySelf()

    @staticmethod
    def _handleStatus_BUILDERFAIL(build, librarian, slave_status, logger):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % build.buildqueue_record.builder.name)
        build.buildqueue_record.builder.failBuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        # simply reset job
        build.storeBuildInfo(build, librarian, slave_status)
        build.buildqueue_record.reset()

    @staticmethod
    def _handleStatus_GIVENBACK(build, librarian, slave_status, logger):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (build.buildqueue_record.specific_job.build.title,
                          build.buildqueue_record.builder.name))
        build.storeBuildInfo(build, librarian, slave_status)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        build.buildqueue_record.builder.cleanSlave()
        build.buildqueue_record.reset()

    @staticmethod
    def getLogFromSlave(build):
        """See `IBuildBase`."""
        return build.buildqueue_record.builder.transferSlaveFileToLibrarian(
            'buildlog', build.buildqueue_record.getLogFileName(),
            build.is_private)

    @staticmethod
    def storeBuildInfo(build, librarian, slave_status):
        """See `IBuildBase`."""
        # XXX michaeln 2010-05-05 bug=567922
        # As this method is temporarily static until BuildBase is
        # removed and the implementation moved to PackageBuild,
        # self.attr_name is temporarily build.attr_name, which
        # means we cannot set the build attributes.
        naked_build = removeSecurityProxy(build)
        naked_build.log = build.getLogFromSlave(build)
        naked_build.builder = build.buildqueue_record.builder
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        naked_build.date_finished = datetime.datetime.now(pytz.UTC)
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

    @staticmethod
    def queueBuild(build, suspended=False):
        """See `IBuildBase`"""
        specific_job = build.makeJob()

        # This build queue job is to be created in a suspended state.
        if suspended:
            specific_job.job.suspend()

        duration_estimate = build.estimateDuration()
        queue_entry = BuildQueue(
            estimated_duration=duration_estimate,
            job_type=build.build_farm_job_type,
            job=specific_job.job, processor=specific_job.processor,
            virtualized=specific_job.virtualized)
        Store.of(build).add(queue_entry)
        return queue_entry

