# Copyright Canonical Limited 2004-2007

import tempfile
import subprocess
import os
import time
import xmlrpclib
import socket
import datetime
import pytz

from sqlobject import SQLObjectNotFound

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical import encoding
from canonical.config import config
from canonical.lp import dbschema
from canonical.librarian.utils import copy_and_close
from canonical.launchpad.interfaces import (
    BuildDaemonError, IBuildQueueSet, BuildJobMismatch, IBuildSet, IBuilderSet,
    ProtocolVersionMismatch, pocketsuffix
    )
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache, cursor)
from canonical.launchpad.helpers import filenameToContentType
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
        # available slaves
        self.builders = getUtility(IBuilderSet).getBuildersByArch(arch)

        # Actualise the results because otherwise we get our exceptions
        # at odd times
        self.logger.debug("Initialising builders for " + arch.architecturetag)

        self.builders = set(self.builders)

        self.logger.debug("Finding XMLRPC clients for the builders")

        for builder in self.builders:
            # builders that are not 'ok' are not worth rechecking here for some
            # currently undocumented reason - RBC 20070523.
            if builder.builderok:
                self.updateBuilderStatus(builder, arch)
        
        # commit the updates made to the builders.
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
            builder.checkCanBuildForDistroArchRelease(arch)
        # catch only known exceptions
        except (ValueError, TypeError, xmlrpclib.Fault,
                socket.error, BuildDaemonError), reason:
            # repr() is required for socket.error
            builder.failbuilder(repr(reason))
            self.logger.debug("Builder on %s marked as failed due to: %r",
                              builder.url, reason, exc_info=True)
        else:
            # Update the successfully probed builder to OK state.
            builder.builderok = True
            builder.failnotes = None
            # verify if the builder slave is working with sane information
            self.rescueBuilderIfLost(builder)

    def rescueBuilderIfLost(self, builder):
        """Reset Builder slave if job information mismatch.

        If builder is BUILDING or WAITING an unknown job clean it.
        Assuming the XMLRPC is working properly at this point.
        """
        status_sentence = builder.slaveStatusSentence()

        # ident_position dict relates the position of the job identifier
        # token in the sentence received from status(), according the
        # two status we care about. See see lib/canonical/buildd/slave.py
        # for further information about sentence format.
        ident_position = {
            'BuilderStatus.BUILDING': 1,
            'BuilderStatus.WAITING': 2
            }

        # isolate the BuilderStatus string, always the first token in
        # status returned sentence, see lib/canonical/buildd/slave.py
        status = status_sentence[0]

        # if slave is not building nor waiting, it's not in need of rescuing.
        if status not in ident_position.keys():
            return

        # extract information from the identifier
        build_id, queue_item_id = status_sentence[ident_position[status]].split('-')

        # check if build_id and queue_item_id exist
        try:
            build = getUtility(IBuildSet).getByBuildID(int(build_id))
            queue_item = getUtility(IBuildQueueSet).get(int(queue_item_id))
            # also check it build and buildqueue are properly related
            if queue_item.build.id != build.id:
                raise BuildJobMismatch('Job build entry mismatch')

        except (SQLObjectNotFound, BuildJobMismatch), reason:
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
        # XXX cprov 20070417: ideally we should be able to notify the
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
        sourcename = queueItem.build.sourcepackagerelease.name
        version = queueItem.build.sourcepackagerelease.version
        # we rely on previous storage of current buildstate
        # in the state handling methods.
        state = queueItem.build.buildstate.name

        dar = queueItem.build.distroarchrelease
        distroname = dar.distrorelease.distribution.name
        distroreleasename = dar.distrorelease.name
        archname = dar.architecturetag

        # logfilename format:
        # buildlog_<DISTRIBUTION>_<DISTRORELEASE>_<ARCHITECTURE>_\
        # <SOURCENAME>_<SOURCEVERSION>_<BUILDSTATE>.txt
        # as:
        # buildlog_ubuntu_dapper_i386_foo_1.0-ubuntu0_FULLYBUILT.txt
        # it fix request from bug # 30617
        logfilename = ('buildlog_%s-%s-%s.%s_%s_%s.txt'
                       % (distroname, distroreleasename,
                          archname, sourcename, version, state))

        return queueItem.builder.transferSlaveFileToLibrarian(
            'buildlog', logfilename)

    def updateBuild(self, queueItem, librarian):
        """Verify the current build job status and perform the required
        actions for each state.
        """
        try:
            res = queueItem.builder.slaveStatusSentence()
        except (xmlrpclib.Fault, socket.error), info:
            # XXX cprov 20050629
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timestamp.
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            self.logger.debug(info, exc_info=True)
            # keep the job for scan
            return

        # res = ('<status>', ..., ...)
        builder_status = res[0]
        builder_status_handlers = {
            'BuilderStatus.IDLE': self.updateBuild_IDLE,
            'BuilderStatus.BUILDING': self.updateBuild_BUILDING,
            'BuilderStatus.ABORTING': self.updateBuild_ABORTING,
            'BuilderStatus.ABORTED': self.updateBuild_ABORTED,
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

        method = builder_status_handlers[builder_status]
        try:
            # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
            slave = removeSecurityProxy(queueItem.builder.slave)
            method(queueItem, slave, librarian, *res[1:])
        except TypeError, e:
            self.logger.critical("Received wrong number of args in response.")
            self.logger.exception(e)

        self.commit()

    def updateBuild_IDLE(self, queueItem, slave, librarian, info):
        """Somehow the builder forgot about the build job, log this and reset
        the record.
        """
        self.logger.warn("Builder on %s is Dory AICMFP. "
                         "Builder forgot about build %s "
                         "-- resetting buildqueue record"
                         % (queueItem.builder.url, queueItem.build.title))

        queueItem.builder = None
        queueItem.buildstart = None
        queueItem.build.buildstate = dbschema.BuildStatus.NEEDSBUILD

    def updateBuild_BUILDING(self, queueItem, slave, librarian, buildid,
                             logtail):
        """Build still building, Simple collects the logtail"""
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, queueItem, slave, librarian, buildid):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """
        queueItem.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, queueItem, slave, librarian, buildid):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.builder.cleanSlave()
        queueItem.builder = None
        queueItem.buildstart = None
        queueItem.build.buildstate = dbschema.BuildStatus.BUILDING

    def updateBuild_WAITING(self, queueItem, slave, librarian, buildstatus,
                            buildid, filemap=None, dependencies=None):
        """Perform the actions needed for a slave in a WAITING state

        Buildslave can be WAITING in five situations:

        * Build has failed, no filemap is received (PACKAGEFAIL, DEPFAIL,
                                                    CHROOTFAIL, BUILDERFAIL)

        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrieve those files and store in
          Librarian with getFileFromSlave() and then pass the binaries to
          the uploader for processing.
        """
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        assert buildstatus.startswith('BuildStatus.')

        buildstatus = buildstatus[len('BuildStatus.'):]
        method = getattr(self, 'buildStatus_' + buildstatus, None)

        if method is None:
            self.logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                                 % (buildstatus, queueItem.builder.url))
            return

        method(queueItem, slave, librarian, buildid, filemap, dependencies)

    def storeBuildInfo(self, queueItem, slave, librarian, buildid,
                       dependencies):
        """Store available information for build jobs.

        Store Buildlog, datebuilt, duration, dependencies.
        """
        queueItem.build.buildlog = self.getLogFromSlave(queueItem)
        queueItem.build.datebuilt = UTC_NOW
        # XXX: This includes scanner latency in the measurement, it should
        # really be asking the slave for the duration spent building.
        # we need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        queueItem.build.buildduration = RIGHT_NOW - queueItem.buildstart
        queueItem.build.builder = queueItem.builder
        queueItem.build.dependencies = dependencies

    def buildStatus_OK(self, queueItem, slave, librarian, buildid,
                       filemap=None, dependencies=None):
        """Handle a package that built successfully.

        Once built successfully, we pull the files, store them in a
        directory, store build information and push them through the
        uploader.
        """
        self.logger.debug("Processing successful build %s" % buildid)
        # Explode before collect a binary that is denied in this
        # distrorelease/pocket
        build = queueItem.build
        if build.archive == build.distrorelease.main_archive:
            assert build.distrorelease.canUploadToPocket(build.pocket), (
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
            "-r", "%s" % (queueItem.build.distrorelease.name +
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

        # XXX cprov 20070417: we do not check uploader_result_code
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

        # Store build information, build record was already updated during
        # the binary upload.
        self.storeBuildInfo(
            queueItem, slave, librarian, buildid, dependencies)

        # The famous 'flush_updates + clear_cache' will make visible the
        # DB changes done in process-upload, considering that the
        # transaction was set with READ_COMMITED_ISOLATION isolation level.
        cur = cursor()
        cur.execute('SHOW transaction_isolation')
        isolation_str = cur.fetchone()[0]
        assert isolation_str == 'read committed', (
            'BuildMaster/BuilderGroup transaction isolation should be '
            'READ_COMMITTED_ISOLATION (not "%s")' % isolation_str)

        flush_database_updates()
        clear_current_connection_cache()

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
            queueItem.build.buildstate = dbschema.BuildStatus.FAILEDTOUPLOAD
            queueItem.build.notify(extra_info=upload_stderr)
        else:
            self.logger.debug("Gathered build %s completely" % queueItem.name)

        # Release the builder for another job.
        queueItem.builder.cleanSlave()
        # Remove BuildQueue record.
        queueItem.destroySelf()
        # Commit the transaction so that the uploader can see the updated
        # build record.
        self.commit()

    def buildStatus_PACKAGEFAIL(self, queueItem, slave, librarian, buildid,
                                filemap=None, dependencies=None):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.FAILEDTOBUILD
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        queueItem.builder.cleanSlave()
        queueItem.build.notify()
        queueItem.destroySelf()

    def buildStatus_DEPFAIL(self, queueItem, slave, librarian, buildid,
                            filemap=None, dependencies=None):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.MANUALDEPWAIT
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        self.logger.critical("***** %s is MANUALDEPWAIT *****"
                             % queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.destroySelf()

    def buildStatus_CHROOTFAIL(self, queueItem, slave, librarian, buildid,
                               filemap=None, dependencies=None):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        queueItem.build.buildstate = dbschema.BuildStatus.CHROOTWAIT
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        self.logger.critical("***** %s is CHROOTWAIT *****" %
                             queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.build.notify()
        queueItem.destroySelf()

    def buildStatus_BUILDERFAIL(self, queueItem, slave, librarian, buildid,
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
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        queueItem.builder = None
        queueItem.buildstart = None

    def buildStatus_GIVENBACK(self, queueItem, slave, librarian, buildid,
                              filemap=None, dependencies=None):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        self.logger.warning("***** %s is GIVENBACK by %s *****"
                            % (buildid, queueItem.builder.name))
        queueItem.build.buildstate = dbschema.BuildStatus.NEEDSBUILD
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        # XXX cprov 20060530: Currently this information is not
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


