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
    IBuildQueueSet, IBuildSet, IBuilderSet, pocketsuffix
    )
from canonical.database.constants import UTC_NOW
from canonical.launchpad.helpers import filenameToContentType
from canonical.buildd.slave import BuilderStatus

class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class ProtocolVersionMismatch(BuildDaemonError):
    """The build slave had a protocol version. This is a serious error."""


class BuildJobMismatch(BuildDaemonError):
    """The build slave is working with mismatched information, needs rescue."""


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
            try:
                # Verify if *trusted* builders has been disabled.
                # Untrusted builders will be always probed.
                if not builder.builderok and builder.trusted:
                    continue

                # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
                slave = removeSecurityProxy(builder.slave)

                # verify the echo method
                if slave.echo("Test")[0] != "Test":
                    raise BuildDaemonError("Failed to echo OK")

                # ask builder information
                # XXX: mechanisms is ignored? -- kiko
                builder_vers, builder_arch, mechanisms = slave.info()

                # attempt to wrong builder version
                if builder_vers != '1.0':
                    raise ProtocolVersionMismatch("Protocol version mismatch")

                # attempt to wrong builder architecture
                if builder_arch != arch.architecturetag:
                    raise BuildDaemonError(
                        "Architecture tag mismatch: %s != %s"
                        % (arch, arch.architecturetag))
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

        self.commit()
        self.updateOkSlaves()

    def rescueBuilderIfLost(self, builder):
        """Reset Builder slave if job information mismatch.

        If builder is BUILDING or WAITING an unknown job clean it.
        Assuming the XMLRPC is working properly at this point.
        """
        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(builder.slave)

        # request slave status sentence
        sentence = slave.status()

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
        status = sentence[0]

        # if slave is not building nor waiting, it's not in need of rescuing.
        if status not in ident_position.keys():
            return

        # extract information from the identifier
        build_id, queue_item_id = sentence[ident_position[status]].split('-')

        # check if build_id and queue_item_id exist
        try:
            build = getUtility(IBuildSet).getByBuildID(int(build_id))
            queue_item = getUtility(IBuildQueueSet).get(int(queue_item_id))
            # also check it build and buildqueue are properly related
            if queue_item.build.id != build.id:
                raise BuildJobMismatch('Job build entry mismatch')

        except (SQLObjectNotFound, BuildJobMismatch), reason:
            slave.clean()
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
        builder.failbuilder(reason)
        self.updateOkSlaves()

    def giveToBuilder(self, builder, libraryfilealias, librarian):
        """Request Slave to download a given file from Librarian.

        Check if builder is working properly, build the librarian URL
        for the given file and use the slave XMLRPC 'doyouhave' method
        to request the download of the file directly by the slave.
        if the slave returns False, which means it wasn't able to
        download or recover from filecache, it tries to download
        the file locally and push it through the XMLRPC interface.
        This last algorithm is bogus and fails most of the time, that's
        why we consider it deprecated and it'll be kept only til the next
        protocol redesign.
        """
        if not builder.builderok:
            raise BuildDaemonError("Attempted to give a file to a known-bad"
                                   " builder")

        url = librarian.getURLForAlias(libraryfilealias.id, is_buildd=True)

        self.logger.debug("Asking builder on %s to ensure it has file %s "
                          "(%s, %s)" % (builder.url, libraryfilealias.filename,
                                        url, libraryfilealias.content.sha1))

        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(builder.slave)
        present, info = slave.ensurepresent(
            libraryfilealias.content.sha1, url)

        if not present:
            message = """Slave '%s' (%s) was unable to fetch file.
            ****** URL ********
            %s
            ****** INFO *******
            %s
            *******************
            """ % (builder.name, builder.url, url, info)
            raise BuildDaemonError(message)

    def findChrootFor(self, build_candidate, pocket):
        """Return the CHROOT librarian identifier for (buildCandidate, pocket).

        Calculate the right CHROOT file for the given pair buildCandidate and
        pocket and return the Librarian file identifier for it, return None
        if it wasn't found or wasn't able to calculate.
        """
        chroot = build_candidate.archrelease.getChroot(pocket)
        if chroot:
            return chroot.content.sha1

    def startBuild(self, builder, queueItem, filemap, buildtype, pocket, args):
        """Request a build procedure according given parameters."""
        buildid = "%s-%s" % (queueItem.build.id, queueItem.id)
        self.logger.debug("Initiating build %s on %s"
                          % (buildid, builder.url))

        # explodes before start building a denied build in distrorelease/pocket
        build = queueItem.build
        assert build.distrorelease.canUploadToPocket(build.pocket), (
            "%s (%s) can not be built for pocket %s: illegal status"
            % (build.title, build.id,
               build.pocket.name))

        # refuse builds for missing CHROOTs
        chroot = self.findChrootFor(queueItem, pocket)
        if not chroot:
            self.logger.critical("OOPS! Could not find CHROOT")
            return
        # store DB information
        queueItem.builder = builder
        queueItem.buildstart = UTC_NOW
        queueItem.build.buildstate = dbschema.BuildStatus.BUILDING
        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(builder.slave)
        status, info = slave.build(buildid, buildtype, chroot, filemap, args)
        message = """%s (%s):
        ***** RESULT *****
        %s: %s
        ******************
        """ % (builder.name, builder.url, status, info)
        self.logger.debug(message)

    def getLogFromSlave(self, slave, queueItem, librarian):
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

        return self.getFileFromSlave(slave, logfilename,
                                     'buildlog', librarian)

    def getFileFromSlave(self, slave, filename, sha1sum, librarian):
        """Request a file from Slave.

        Protocol version 1.0new or higher provides /filecache/
        which allows us to be clever in large file transfer. This method
        Receive a file identifier (sha1sum) a MIME header filename and a
        librarian instance. Store the incomming file in Librarian and return
        the file alias_id, if it failed return None. 'buildlog' string is a
        special identifier which recover the raw last slave buildlog,
        compress it locally using gzip and finally store the compressed
        copy in librarian.
        """
        aliasid = None
        # ensure the tempfile will return a proper name, which does not
        # confuses the gzip as suffixes like '-Z', '-z', almost everything
        # insanely related to 'z'. Might also be solved by bug # 3111
        out_file_fd, out_file_name = tempfile.mkstemp(suffix=".tmp")

        try:
            out_file = os.fdopen(out_file_fd, "r+")
            slave_file = slave.getFile(sha1sum)
            copy_and_close(slave_file, out_file)

            # if the requested file is the 'buildlog' compress it using gzip
            # before storing in Librarian
            if sha1sum == 'buildlog':
                # XXX cprov 20051010:
                # python.gzip presented weird errors at this point, most
                # related to incomplete file storage, the compressed file
                # was prematurely finished in a 0x00. Using system call for
                # while -> bug # 3111
                os.system('gzip -9 %s' % out_file_name)
                # modify the local and header filename
                filename += '.gz'
                out_file_name += '.gz'

            # repopen the file, seek to its end position, count and seek
            # to beginning, ready for adding to the Librarian.
            out_file = open(out_file_name)
            out_file.seek(0, 2)
            bytes_written = out_file.tell()
            out_file.seek(0)
            ftype = filenameToContentType(filename)

            aliasid = librarian.addFile(filename, bytes_written,
                                        out_file, contentType=ftype)
        finally:
            # Finally, remove the temporary file
            out_file.close()
            os.remove(out_file_name)

        return aliasid

    def updateBuild(self, queueItem, librarian):
        """Verify the current build job status and perform the required
        actions for each state.
        """
        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(queueItem.builder.slave)

        try:
            res = slave.status()
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
        status = res[0]

        assert status.startswith('BuilderStatus.')

        status = status[len('BuilderStatus.'):]
        method = getattr(self, 'updateBuild_' + status, None)

        if method is None:
            self.logger.critical("Builder on %s returned unknown status %s,"
                                 " failing it" % (queueItem.builder.url,
                                                  status))
            self.failBuilder(queueItem.builder,
                             ("Unknown status code (%s) returned from "
                              "status() probe." % status))
            queueItem.builder = None
            queueItem.buildstart = None
            self.commit()
            return

        try:
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
        queueItem.builder = None
        queueItem.buildstart = None
        queueItem.build.buildstate = dbschema.BuildStatus.BUILDING
        slave.clean()

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
        queueItem.build.buildlog = self.getLogFromSlave(slave, queueItem,
                                                        librarian)
        queueItem.build.datebuilt = UTC_NOW
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
            uploader_argv, stdout=subprocess.PIPE)

        # nothing would be written to the stdout/stderr, but it's safe
        stdout, stderr = uploader_process.communicate()
        result_code = uploader_process.returncode

        if os.path.exists(upload_dir):
            self.logger.debug("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            os.makedirs(failed_dir)
            os.rename(
                upload_dir, os.path.join(failed_dir, upload_leaf))

        self.logger.debug("Uploader returned %d" % result_code)

        self.logger.debug("Gathered build of %s completely"
                          % queueItem.name)
        # store build info
        queueItem.build.buildstate = dbschema.BuildStatus.FULLYBUILT
        self.storeBuildInfo(queueItem, slave, librarian, buildid, dependencies)
        queueItem.destroySelf()

        # release the builder
        slave.clean()

        # Commit the transaction so that the uploader can see the updated
        # build record
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
        slave.clean()
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
        slave.clean()
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
        slave.clean()
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
        slave.clean()
        # XXX cprov 20060530: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
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
            if builder.builderok:
                if builder.manual:
                    continue
                if builder.trusted != is_trusted:
                    continue
                # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
                slave = removeSecurityProxy(builder.slave)
                try:
                    slavestatus = slave.status()
                except (xmlrpclib.Fault, socket.error), info:
                    continue
                if slavestatus[0] == BuilderStatus.IDLE:
                    return builder

        return None


