# Copyright Canonical Limited 2004-2007
"""Builder Group model.

Implement methods to deal with builder and their results.
"""

__metaclass__ = type

import datetime
import os
import pytz
import socket
import subprocess
import time
import xmlrpclib

from sqlobject import SQLObjectNotFound

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.lp import dbschema
from canonical.librarian.interfaces import ILibrarianClient
from canonical.librarian.utils import copy_and_close
from canonical.launchpad.interfaces import (
    BuildDaemonError, IBuildQueueSet, BuildJobMismatch, IBuildSet, IBuilderSet,
    NotFoundError, pocketsuffix
    )
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache, cursor)
from canonical.buildd.slave import BuilderStatus


class BuilderGroup:
    """Manage a set of builders based on a given architecture"""

    def commit(self):
        self._tm.commit()

    def __init__(self, logger, tm):
        self._tm = tm
        self.logger = logger

    def checkAvailableSlaves(self, arch):
        """Iter through available builder-slaves for an given architecture."""
        # Get available slaves for the context architecture.
        self.builders = getUtility(IBuilderSet).getBuildersByArch(arch)

        # Actualise the results because otherwise we get our exceptions
        # at odd times
        self.logger.debug("Initialising builders for " + arch.architecturetag)

        self.builders = set(self.builders)

        self.logger.debug("Finding XMLRPC clients for the builders")

        for builder in self.builders:
            # XXX RBC 2007-05-23 bug 31546, 30633: builders that are not 'ok'
            # are not worth rechecking here for some currently undocumented
            # reason.
            if builder.builderok:
                self.updateBuilderStatus(builder, arch)

        # Commit the updates made to the builders.
        self.commit()
        self.updateOkSlaves()

    def updateBuilderStatus(self, builder, arch):
        """Update the status for a builder by probing it.

        :param builder: A builder object.
        :param arch: The expected architecture family of the builder.
        """
        self.logger.info('Checking %s' % builder.name)
        try:
            builder.checkSlaveAlive()
            builder.checkCanBuildForDistroArchSeries(arch)
        # Catch only known exceptions.
        # XXX cprov 2007-06-15 bug=120571: ValueError & TypeError catching is
        # disturbing in this context. We should spend sometime sanitizing the
        # exceptions raised in the Builder API since we already started the
        # main refactoring of this area.
        except (ValueError, TypeError, xmlrpclib.Fault,
                socket.error, BuildDaemonError), reason:
            # XXX cprov 2007-06-15: repr() is required for socket.error,
            # however it's not producing anything 'readable' on
            # Builder.failurenotes. it need attention at some point.
            builder.failbuilder(repr(reason))
            self.logger.debug("Builder on %s marked as failed due to: %r",
                              builder.url, reason, exc_info=True)
        else:
            # Verify if the builder slave is working with sane information.
            self.rescueBuilderIfLost(builder)

    def rescueBuilderIfLost(self, builder):
        """Reset Builder slave if job information doesn't match with DB.

        If builder is BUILDING or WAITING but has an information record
        that doesn't match what is stored in the DB, we have to dismiss
        its current actions and let the slave free for another job,
        assuming the XMLRPC is working properly at this point.
        """
        status_sentence = builder.slaveStatusSentence()

        # 'ident_position' dict relates the position of the job identifier
        # token in the sentence received from status(), according the
        # two status we care about. See see lib/canonical/buildd/slave.py
        # for further information about sentence format.
        ident_position = {
            'BuilderStatus.BUILDING': 1,
            'BuilderStatus.WAITING': 2
            }

        # Isolate the BuilderStatus string, always the first token in
        # see lib/canonical/buildd/slave.py and
        # IBuilder.slaveStatusSentence().
        status = status_sentence[0]

        # If slave is not building nor waiting, it's not in need of rescuing.
        if status not in ident_position.keys():
            return

        # Extract information from the identifier.
        build_id, queue_item_id = status_sentence[
            ident_position[status]].split('-')

        # Check if build_id and queue_item_id exist.
        try:
            build = getUtility(IBuildSet).getByBuildID(int(build_id))
            queue_item = getUtility(IBuildQueueSet).get(int(queue_item_id))
            # Also check it build and buildqueue are properly related.
            if queue_item.build.id != build.id:
                raise BuildJobMismatch('Job build entry mismatch')

        except (SQLObjectNotFound, NotFoundError, BuildJobMismatch), reason:
            if status == 'BuilderStatus.WAITING':
                builder.cleanSlave()
            else:
                builder.requestAbort()
            self.logger.warn("Builder '%s' rescued from '%s-%s: %s'" % (
                builder.name, build_id, queue_item_id, reason))

    def updateOkSlaves(self):
        """Build the 'okslaves' list

        'okslaves' will contains the list of builder instances signed with
        builder.builderok == true. Emits a log.warn message if no builder
        were found.
        """
        self.okslaves = [builder for builder in self.builders
                         if builder.builderok]
        if not self.okslaves:
            self.logger.warn("No builders are available")

    def failBuilder(self, builder, reason):
        """Mark builder as failed.

        Set builderok as False, store the reason in failnotes and update
        the list of working builders (self.okslaves).
        """
        # XXX cprov 2007-04-17: ideally we should be able to notify the
        # the buildd-admins about FAILED builders. One alternative is to
        # make the buildd_cronscript (slave-scanner, in this case) to exit
        # with error, for those cases buildd-sequencer automatically sends
        # an email to admins with the script output.
        builder.failbuilder(reason)
        self.updateOkSlaves()

    def getLogFromSlave(self, queueItem):
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """
        return queueItem.builder.transferSlaveFileToLibrarian(
            'buildlog', queueItem.getLogFileName())

    def updateBuild(self, queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.
        """
        try:
            (builder_status, build_id, build_status, logtail, filemap,
             dependencies) = queueItem.builder.slaveStatus()
        except (xmlrpclib.Fault, socket.error), info:
            # XXX cprov 2005-06-29:
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timestamp.
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            self.logger.debug(info, exc_info=True)
            # keep the job for scan
            return

        builder_status_handlers = {
            'BuilderStatus.IDLE': queueItem.updateBuild_IDLE,
            'BuilderStatus.BUILDING': queueItem.updateBuild_BUILDING,
            'BuilderStatus.ABORTING': queueItem.updateBuild_ABORTING,
            'BuilderStatus.ABORTED': queueItem.updateBuild_ABORTED,
            'BuilderStatus.WAITING': self.updateBuild_WAITING,
            }

        if builder_status not in builder_status_handlers:
            self.logger.critical(
                "Builder on %s returned unknown status %s, failing it"
                % (queueItem.builder.url, builder_status))
            self.failBuilder(
                queueItem.builder,
                "Unknown status code (%s) returned from status() probe."
                % builder_status)
            queueItem.builder = None
            queueItem.buildstart = None
            self.commit()
            return

        # Since logtail is a xmlrpclib.Binary container and it is returned
        # from the IBuilder content class, it arrives protected by a Zope
        # Security Proxy, which is not declared, thus empty. Before passing
        # it to the status handlers we will simply remove the proxy.
        logtail = removeSecurityProxy(logtail)

        method = builder_status_handlers[builder_status]
        try:
            # XXX cprov 2007-05-25: We need this code for WAITING status
            # handler only until we are able to also move it to
            # BuildQueue content class and avoid to pass 'queueItem'.
            if builder_status == 'BuilderStatus.WAITING':
                method(queueItem, build_id, build_status, logtail,
                       filemap, dependencies, self.logger)
            else:
                method(build_id, build_status, logtail,
                       filemap, dependencies, self.logger)
        except TypeError, e:
            self.logger.critical("Received wrong number of args in response.")
            self.logger.exception(e)

        self.commit()

    def updateBuild_WAITING(self, queueItem, buildid, build_status,
                            logtail, filemap, dependencies, logger):
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

        # XXX: dsilvers 2005-03-02: Confirm the builder has the right build?
        assert build_status.startswith('BuildStatus.'), (
            'Malformed status string: %s' % build_status)

        buildstatus = build_status[len('BuildStatus.'):]
        method = getattr(self, 'buildStatus_' + buildstatus, None)

        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (buildstatus, queueItem.builder.url))
            return

        method(queueItem, librarian, buildid, filemap, dependencies)

    def storeBuildInfo(self, queueItem, librarian, buildid, dependencies):
        """Store available information for build jobs.

        Store Buildlog, datebuilt, duration, dependencies.
        """
        queueItem.build.buildlog = self.getLogFromSlave(queueItem)
        queueItem.build.builder = queueItem.builder
        queueItem.build.dependencies = dependencies
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        queueItem.build.datebuilt = UTC_NOW
        # We need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        queueItem.build.buildduration = RIGHT_NOW - queueItem.buildstart


    def buildStatus_OK(self, queueItem, librarian, buildid,
                       filemap=None, dependencies=None):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        # XXX cprov 2007-07-11 bug=129487: untested code path.

        self.logger.debug("Processing successful build %s" % buildid)
        # Explode before collect a binary that is denied in this
        # distroseries/pocket
        build = queueItem.build
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
        self.logger.debug("Storing build result at '%s'" % upload_dir)

        # build the right UPLOAD_PATH so the distribution and archive
        # can be correctly found during the upload:
        #  * For trusted:        <distribution>/[FILES]
        #  * For PPA(untrusted): ~<person>/<distribution>/[FILES]
        distribution_name = queueItem.build.distribution.name
        if queueItem.is_trusted:
            target_path = "%s" % distribution_name
        else:
            archive = queueItem.build.archive
            target_path = "~%s/%s" % (archive.owner.name, distribution_name)
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
        self.logger.debug("Saving uploader log at '%s'"
                          % uploader_logfilename)

        # add extra arguments for processing a binary upload
        extra_args = [
            "--log-file", "%s" %  uploader_logfilename,
            "-d", "%s" % queueItem.build.distribution.name,
            "-s", "%s" % (queueItem.build.distroseries.name +
                          pocketsuffix[queueItem.build.pocket]),
            "-b", "%s" % queueItem.build.id,
            "-J", "%s" % upload_leaf,
            "%s" % root,
            ]

        uploader_argv.extend(extra_args)

        self.logger.debug("Invoking uploader on %s" % root)
        self.logger.debug("%s" % uploader_argv)

        uploader_process = subprocess.Popen(
            uploader_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Nothing should be written to the stdout/stderr.
        upload_stdout, upload_stderr = uploader_process.communicate()

        # XXX cprov 2007-04-17: we do not check uploader_result_code
        # anywhere. We need to find out what will be best strategy
        # when it failed HARD (there is a huge effort in process-upload
        # to not return error, it only happen when the code is broken).
        uploader_result_code = uploader_process.returncode
        self.logger.debug("Uploader returned %d" % uploader_result_code)

        # Quick and dirty hack to carry on on process-upload failures
        if os.path.exists(upload_dir):
            self.logger.debug("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            if not os.path.exists(failed_dir):
                os.mkdir(failed_dir)
            os.rename(upload_dir, os.path.join(failed_dir, upload_leaf))

        # The famous 'flush_updates + clear_cache' will make visible the
        # DB changes done in process-upload, considering that the
        # transaction was set with READ_COMMITED_ISOLATION isolation level.
        cur = cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        assert isolation_str == 'read committed', (
            'BuildMaster/BuilderGroup transaction isolation should be '
            'READ_COMMITTED_ISOLATION (not "%s")' % isolation_str)

        original_slave = queueItem.builder.slave

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
        build = getUtility(IBuildSet).getByBuildID(queueItem.build.id)
        if (build.buildstate != dbschema.BuildStatus.FULLYBUILT or
            len(build.binarypackages) == 0):
            self.logger.debug("Build %s upload failed." % build.id)
            # update builder
            queueItem.build.buildstate = dbschema.BuildStatus.FAILEDTOUPLOAD
            # Retrieve log file content.
            possible_locations = (
                'failed', 'failed-to-move', 'rejected', 'accepted')
            for location_dir in possible_locations:
                upload_final_location = os.path.join(
                    root, location_dir, upload_leaf)
                if os.path.exists(upload_final_location):
                    log_filepath = os.path.join(
                        upload_final_location, 'uploader.log')
                    try:
                        uploader_log_file = open(log_filepath)
                        uploader_log_content = uploader_log_file.read()
                    finally:
                        uploader_log_file.close()
                    break
            else:
                uploader_log_content = 'Could not find upload log file'
            # Notify the build failure.
            queueItem.build.notify(extra_info=uploader_log_content)
        else:
            self.logger.debug("Gathered build %s completely" % queueItem.name)

        # Release the builder for another job.
        queueItem.builder.cleanSlave()
        # Remove BuildQueue record.
        queueItem.destroySelf()
        # Commit the transaction so that the uploader can see the updated
        # build record.
        self.commit()

    def buildStatus_PACKAGEFAIL(self, queueItem, librarian, buildid,
                                filemap=None, dependencies=None):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.FAILEDTOBUILD
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        queueItem.builder.cleanSlave()
        queueItem.build.notify()
        queueItem.destroySelf()

    def buildStatus_DEPFAIL(self, queueItem, librarian, buildid,
                            filemap=None, dependencies=None):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.MANUALDEPWAIT
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        self.logger.critical("***** %s is MANUALDEPWAIT *****"
                             % queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.destroySelf()

    def buildStatus_CHROOTFAIL(self, queueItem, librarian, buildid,
                               filemap=None, dependencies=None):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.CHROOTWAIT
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        self.logger.critical("***** %s is CHROOTWAIT *****" %
                             queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.build.notify()
        queueItem.destroySelf()

    def buildStatus_BUILDERFAIL(self, queueItem, librarian, buildid,
                                filemap=None, dependencies=None):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        self.logger.warning("***** %s has failed *****"
                            % queueItem.builder.name)
        self.failBuilder(queueItem.builder,
                         ("Builder returned BUILDERFAIL when asked "
                          "for its status"))
        # simply reset job
        queueItem.build.buildstate = dbschema.BuildStatus.NEEDSBUILD
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        queueItem.builder = None
        queueItem.buildstart = None

    def buildStatus_GIVENBACK(self, queueItem, librarian, buildid,
                              filemap=None, dependencies=None):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        self.logger.warning("***** %s is GIVENBACK by %s *****"
                            % (buildid, queueItem.builder.name))
        queueItem.build.buildstate = dbschema.BuildStatus.NEEDSBUILD
        self.storeBuildInfo(queueItem, librarian, buildid, dependencies)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        queueItem.builder.cleanSlave()
        queueItem.builder = None
        queueItem.buildstart = None
        queueItem.logtail = None
        queueItem.lastscore = 0

    def firstAvailable(self, is_trusted=False):
        """Return the first available builder slave.

        Refuse failed and MANUAL MODE slaves.
        Control whether or not the builder should be *trusted* via
        'is_trusted' given argument, by default *untrusted* build
        are returned.
        Return None if there is none available.
        """
        for builder in self.builders:
            #self.logger.debug('Probing: %s' % builder.url)
            if not builder.builderok:
                #self.logger.debug('builder not OK')
                continue
            if builder.manual:
                #self.logger.debug('builder in MANUAL')
                continue
            if builder.trusted != is_trusted:
                #self.logger.debug('builder INCOMPATIBLE')
                continue
            try:
                slavestatus = builder.slaveStatusSentence()
            except (xmlrpclib.Fault, socket.error), info:
                #self.logger.debug('builder DEAD')
                continue
            if slavestatus[0] != BuilderStatus.IDLE:
                #self.logger.debug('builder not IDLE')
                continue
            return builder

        return None


