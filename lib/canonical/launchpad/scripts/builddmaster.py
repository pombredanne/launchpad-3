#Copyright Canonical Limited 2005-2004
#Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>

"""Common code for Buildd scripts

Module used by buildd-queue-builder.py and buildd-slave-scanner.py
cronscripts.
"""

__metaclass__ = type

__all__ = ['BuilddMaster']


import logging
import xmlrpclib
import socket
import datetime
import pytz
import tempfile
import os
import apt_pkg
import subprocess
import time

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from sqlobject import SQLObjectNotFound

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.interfaces import (
    IBuilderSet, IBuildQueueSet, IBuildSet, pocketsuffix
    )

from canonical.lp import dbschema
from canonical import encoding
from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.launchpad.helpers import filenameToContentType

from canonical.buildd.slave import BuilderStatus
from canonical.buildd.utils import notes

# Constants used in build scoring
SCORE_SATISFIEDDEP = 5
SCORE_UNSATISFIEDDEP = 10

KBYTE = 1024


# this dict maps the package version relationship syntax in lambda
# functions which returns boolean according the results of
# apt_pkg.VersionCompare function (see the order above).
# For further information about pkg relationship syntax see:
#
# http://www.debian.org/doc/debian-policy/ch-relationships.html
#
version_relation_map = {
    # any version is acceptable if no relationship is given
    '': lambda x: True,
    # stricly later
    '>>': lambda x: x == 1,
    # later or equal
    '>=': lambda x: x >= 0,
    # stricly equal
    '=': lambda x: x == 0,
    # earlier or equal
    '<=': lambda x: x <= 0,
    # strictly ealier
    '<<': lambda x: x == -1
}


def file_chunks(from_file, chunk_size=256*KBYTE):
    """Using the special two-arg form of iter() iterate a file's chunks.

    Returns an iterator yielding chunks from the file of size chunk_size
    """
    return iter(lambda: from_file.read(chunk_size), '')

class BuildDaemonPackagesArchSpecific:
    """Parse and implement "PackagesArchSpecific"."""

    def __init__(self, pas_dir, distrorelease):
        self.pas_file = os.path.join(pas_dir, "Packages-arch-specific")
        self.distrorelease = distrorelease
        self.permit = {}
        self._parsePAS()

    def _parsePAS(self):
        """Parse self.pas_file and construct the permissible arch lists."""
        try:
            fd = open(self.pas_file, "r")
        except IOError:
            return

        all_archs = set([a.architecturetag for a in
                         self.distrorelease.architectures])
        for line in fd:
            if "#" in line:
                line = line[:line.find("#")]
            line = line.strip()
            if line == "":
                continue
            is_source = False
            if line.startswith("%"):
                is_source = True
                line = line[1:]

            if not is_source:
                # XXX: dsilvers: 20060201: This is here because otherwise
                # we have too many false positives for now. In time we need
                # to change the section below to use the binary line from
                # the dsc instead of the publishing records. But this is
                # currently not in the database. Bug#30264
                continue
            pkgname, archs = line.split(":", 1)
            is_exclude = False
            if "!" in archs:
                is_exclude = True
                archs = archs.replace("!", "")
            line_archs = archs.strip().split()
            archs = set()
            for arch in line_archs:
                if arch in all_archs:
                    archs.add(arch)
            if is_exclude:
                archs = all_archs - archs
            if not archs:
                # None of the architectures listed affect us.
                if is_source:
                    # But if it's a src pkg then we can still use the
                    # information
                    self.permit[pkgname] = set()
                continue

            if not is_source:
                # We need to find a sourcepackagename
                # If the sourcepackagename changes across arch then
                # we'll have problems. We assume this'll never happen
                arch = archs.pop()
                archs.add(arch)
                distroarchrelease = self.distrorelease[arch]
                try:
                    pkgs = distroarchrelease.getReleasedPackages(pkgname)
                except SQLObjectNotFound:
                    # Can't find it at all...
                    continue
                if not pkgs:
                    # Can't find it, so give up
                    continue
                pkg = pkgs[0].binarypackagerelease
                src_pkg = pkg.build.sourcepackagerelease
                pkgname = src_pkg.sourcepackagename.name
            self.permit[pkgname] = archs

        fd.close()


# XXX cprov 20050628
# I couldn't found something similar in hct.utils, but probably there is.
# as soon as I can get a brief talk with Scott, this code must be removed.
def extractNameAndVersion(filename):
    """ Extract name and version from the filename.

    >>> extractNameAndVersion('at_3.1.8-11ubuntu2_i386.deb')
    ('at', '3.1.8-11ubuntu2')

    """
    name, version, ignored = filename.split("_", 3)[:3]
    return name, version

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
            # verify if the builder has been disabled
            if not builder.builderok:
                continue
            try:
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
                # XXX cprov 20051026: repr() is required for socket.error
                builder.failbuilder(repr(reason))
                self.logger.debug("Builder on %s marked as failed due to: %r",
                                  builder.url, reason, exc_info=True)
            else:
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
        out_file = os.fdopen(out_file_fd, "r+")

        try:
            slave_file = slave.getFile(sha1sum)

            # Read back and save the file 256kb at a time, by using the
            # two-arg form of iter, see
            # /usr/share/doc/python2.4/html/lib/built-in-funcs.html#l2h-42
            bytes_written = 0
            for chunk in file_chunks(slave_file):
                out_file.write(chunk)
                bytes_written += len(chunk)

            slave_file.close()
            out_file.seek(0)

            # if the requested file is the 'buildlog' compress it using gzip
            # before storing in Librarian
            if sha1sum == 'buildlog':
                out_file.close()
                # XXX cprov 20051010:
                # python.gzip presented weird errors at this point, most
                # related to incomplete file storage, the compressed file
                # was prematurely finished in a 0x00. Using system call for
                # while -> bug # 3111
                os.system('gzip -9 %s' % out_file_name)
                # modify the local and header filename
                filename += '.gz'
                out_file_name += '.gz'
                # repopen the currently compressed file, seeks its end
                # position and return to begin, ready for Librarian
                out_file = open(out_file_name)
                out_file.seek(0, 2)
                bytes_written = out_file.tell()
                out_file.seek(0)

            # figure out the MIME content-type
            ftype = filenameToContentType(filename)
            # upload it to the librarian...
            aliasid = librarian.addFile(filename, bytes_written,
                                        out_file,
                                        contentType=ftype)
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
        # <BUILDMASTER_ROOT>/incoming/<BUILD_ID>/files/
        root = os.path.abspath(config.builddmaster.root)
        if not os.path.isdir(root):
            self.logger.debug("Creating BuilddMaster root '%s'"
                              % root)
            os.mkdir(root)

        incoming = os.path.join(root, 'incoming')
        if not os.path.isdir(incoming):
            self.logger.debug("Creating Incoming directory '%s'"
                              % incoming)
            os.mkdir(incoming)
        # create a single directory to store build result files
        upload_leaf = "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"), buildid)
        upload_dir = os.path.join(incoming, upload_leaf)
        os.mkdir(upload_dir)
        self.logger.debug("Storing build result at '%s'" % upload_dir)

        for filename in filemap:
            slave_file = slave.getFile(filemap[filename])
            out_file_name = os.path.join(upload_dir, filename)
            out_file = open(out_file_name, "wb")
            try:
                for chunk in file_chunks(slave_file):
                    out_file.write(chunk)
            finally:
                slave_file.close()
                out_file.close()

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
        uploader_process = subprocess.Popen(uploader_argv,
                                            stdout=subprocess.PIPE)
        # nothing would be written to the stdout/stderr, but it's safe
        stdout, stderr = uploader_process.communicate()
        result_code = uploader_process.returncode

        if os.path.exists(upload_dir):
            self.logger.debug("The upload directory did not get moved.")
            failed_dir = os.path.join(root, "failed-to-move")
            if not os.path.exists(failed_dir):
                os.mkdir(failed_dir)
            os.rename(upload_dir, os.path.join(failed_dir,
                                               upload_leaf))

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
        # XXX cprov 20050823
        # find a way to avoid job being processed for the same slave
        # next round.
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

    def countAvailable(self):
        """Return the number of available builder slaves.

        Return the number of not failed, accessible and IDLE slave.
        Do not count failed and MANUAL MODE slaves.
        """
        count = 0
        for builder in self.builders:
            if builder.builderok:
                # refuse builders in MANUAL MODE
                if builder.manual:
                    self.logger.debug("Builder %s wasn't count due it is in "
                                      "MANUAL MODE." % builder.url)
                    continue

                # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
                slave = removeSecurityProxy(builder.slave)

                try:
                    slavestatus = slave.status()
                except (xmlrpclib.Fault, socket.error), info:
                    self.logger.debug("Builder %s wasn't counted due to (%s)."
                                      % (builder.url, info))
                    continue

                # ensure slave is IDLE
                if slavestatus[0] == BuilderStatus.IDLE:
                    count += 1
        return count

    def firstAvailable(self):
        """Return the first available builder slave.

        Refuse failed and MANUAL MODE slaves. Return None if there is none
        available.
        """
        for builder in self.builders:
            if builder.builderok:
                if builder.manual:
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


class BuilddMaster:
    """Canonical autobuilder master, toolkit and algorithms.

    Attempt to '_archreleases'  attribute, a dictionary which contains a
    chain of verified DistroArchReleases (by addDistroArchRelease) followed
    by another dictionary containing the available builder-slaver for this
    DistroArchRelease, like :

    # associate  specific processor family to a group of available
    # builder-slaves
    notes[archrelease.processorfamily]['builders'] = builderGroup

    # just to consolidate we have a collapsed information
    buildersByProcessor = notes[archrelease.processorfamily]['builders']

    # associate the extended builderGroup reference to a given
    # DistroArchRelease
    self._archreleases[DAR]['builders'] = buildersByProcessor
    """
    def __init__(self, logger, tm):
        self._logger = logger
        self._tm = tm
        self.librarian = getUtility(ILibrarianClient)
        self._archreleases = {}
        # apt_pkg requires InitSystem to get VersionCompare working properly
        apt_pkg.InitSystem()
        self._logger.info("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def addDistroArchRelease(self, distroarchrelease):
        """Setting up a workable DistroArchRelease for this session."""
        self._logger.info("Adding DistroArchRelease %s/%s/%s"
                          % (distroarchrelease.distrorelease.distribution.name,
                             distroarchrelease.distrorelease.name,
                             distroarchrelease.architecturetag))

        # check ARCHRELEASE across available pockets
        for pocket in dbschema.PackagePublishingPocket.items:
            if distroarchrelease.getChroot(pocket):
                # Fill out the contents
                self._archreleases.setdefault(distroarchrelease, {})

    def setupBuilders(self, archrelease):
        """Setting up a group of builder slaves for a given DistroArchRelease.

        Use the annotation utility to store a BuilderGroup instance
        keyed by the the DistroArchRelease.processorfamily in the
        global registry 'notes' and refer to this 'note' in the private
        attribute '_archrelease' keyed by the given DistroArchRelease
        and the label 'builders'. This complicated arrangement enables us
        to share builder slaves between different DistroArchRelases since
        their processorfamily values are the same (compatible processors).
        """
        # Determine the builders for this distroarchrelease...
        builders = self._archreleases[archrelease].get("builders")

        # if annotation for builders was already done, return
        if builders:
            return

        # query the global annotation registry and verify if
        # we have already done the builder checks for the
        # processor family in question. if it's already done
        # simply refer to that information in the _archreleases
        # attribute.
        if 'builders' not in notes[archrelease.processorfamily]:

            # setup a BuilderGroup object
            info = "builders.%s" % archrelease.processorfamily.name
            builderGroup = BuilderGroup(self.getLogger(info), self._tm)

            # check the available slaves for this archrelease
            builderGroup.checkAvailableSlaves(archrelease)

            # annotate the group of builders for the
            # DistroArchRelease.processorfamily in question and the
            # label 'builders'
            notes[archrelease.processorfamily]["builders"] = builderGroup

        # consolidate the annotation for the architecture release
        # in the private attribute _archreleases
        builders = notes[archrelease.processorfamily]["builders"]
        self._archreleases[archrelease]["builders"] = builders

    def createMissingBuilds(self, distrorelease):
        """Iterate over published package and ensure we have a proper
        build entry for it.
        """
        # Do not create builds for distroreleases with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distrorelease.nominatedarchindep:
            self._logger.warn("No Nominated Architecture Independent, skipping"
                              " distrorelease %s", distrorelease.title)
            return


        pas_verify = BuildDaemonPackagesArchSpecific(config.builddmaster.root,
                                                     distrorelease)

        # 1. get all sourcepackagereleases published or pending in this
        # distrorelease
        sources_published = distrorelease.getAllReleasesByStatus(
            dbschema.PackagePublishingStatus.PUBLISHED
            )

        self._logger.info("Scanning publishing records for %s/%s...",
                          distrorelease.distribution.title,
                          distrorelease.title)

        self._logger.info("Found %d source(s) published.",
                          sources_published.count())

        # 2. Determine the set of distroarchreleases we care about in this
        # cycle
        # XXX cprov 20060221: this approach is used several times in this code,
        # it retrieves all the information available from the DB and handle it
        # within the python domain, which is really slow and confusing.
        archs = set()
        initialized_arch_ids = [arch.id for arch in self._archreleases]

        for wanted_arch in distrorelease.architectures:
            if wanted_arch.id in initialized_arch_ids:
                archs.add(wanted_arch)

        self._logger.info("Supported %s"
                          % " ".join([a.architecturetag for a in archs]))

        # XXX cprov 20050831
        # Avoid entering in the huge loop if we don't find at least
        # one supported  architecture. Entering in it with no supported
        # architecture results in a corruption of the persistent DBNotes
        # instance for self._archreleases, it ends up empty.
        if not archs:
            self._logger.info("No Supported Architectures found, skipping "
                              "distrorelease %s", distrorelease.title)
            return

        # 3. For each of the sourcepackagereleases, find its builds...
        for pubrec in sources_published:
            header = ("Build Record %s-%s for '%s' " %
                      (pubrec.sourcepackagerelease.name,
                       pubrec.sourcepackagerelease.version,
                       pubrec.sourcepackagerelease.architecturehintlist))

            # Abort packages with empty architecturehintlist, they are simply
            # wrong.
            # XXX cprov 20050931
            # This check should be done earlier in the upload component/hct
            if pubrec.sourcepackagerelease.architecturehintlist is None:
                self._logger.debug(header + "ABORT EMPTY ARCHHINTLIST")
                continue

            hintlist = pubrec.sourcepackagerelease.architecturehintlist
            if hintlist == 'any':
                hintlist = " ".join([arch.architecturetag for arch in archs])

            # Verify if the sourcepackagerelease build in ALL or ANY arch
            # in this case only one build entry is needed.
            if hintlist == 'all':
                # it's already there, skip to next package
                if pubrec.sourcepackagerelease.builds:
                    # self._logger.debug(header + "SKIPPING ALL")
                    continue

                # packages with an architecture hint of "all" are
                # architecture independent.  Therefore we only need
                # to build on one architecture, the distrorelease.
                # nominatedarchindep
                processor = distrorelease.nominatedarchindep.default_processor
                pubrec.sourcepackagerelease.createBuild(
                    distroarchrelease=distrorelease.nominatedarchindep,
                    processor=processor,
                    pocket=pubrec.pocket)
                self._logger.debug(header + "CREATING ALL (%s)"
                                   % pubrec.pocket.name)
                continue

            # the sourcepackage release builds in a specific list of
            # architetures or in ANY.
            # it should be cross-combined with the current supported
            # architetures in this distrorelease.
            for arch in archs:
                # if the sourcepackagerelease doesn't build in ANY
                # architecture and the current architecture is not
                # mentioned in the list, continues
                supported = True
                if pubrec.sourcepackagerelease.name in pas_verify.permit:
                    if (arch.architecturetag not in
                        pas_verify.permit[pubrec.sourcepackagerelease.name]):
                        supported = False
                if not supported:
                    supported_list = hintlist.split()
                    if arch.architecturetag in supported_list:
                        supported = True
                if not supported:
                    # self._logger.debug(header + "NOT SUPPORTED/WANTED %s" %
                    #                    arch.architecturetag)
                    continue

                # verify is isn't already present for this distroarchrelease
                if not pubrec.sourcepackagerelease.getBuildByArch(arch):
                    # XXX cprov 20050831
                    # I could possibly be better designed, let's think about
                    # it in the future. Pick the first processor we found for
                    # this distroarchrelease.processorfamily. The data model
                    # should change to have a default processor for a
                    # processorfamily
                    # XXX cprov 20060210: no security proxy for dbschema
                    # is annoying
                    pubrec.sourcepackagerelease.createBuild(
                        distroarchrelease=arch,
                        processor=arch.default_processor,
                        pocket=pubrec.pocket)
                    self._logger.debug(header + "CREATING %s (%s)"
                                       % (arch.architecturetag,
                                          pubrec.pocket.name))

        self.commit()

    def addMissingBuildQueueEntries(self):
        """Create missing Buildd Jobs. """
        self._logger.info("Scanning for build queue entries that are missing")
        # Get all builds in NEEDSBUILD which are for a distroarchrelease
        # that we build...
        if not self._archreleases:
            self._logger.warn("No DistroArchrelease Initialized")
            return

        buildset = getUtility(IBuildSet)
        builds = buildset.getPendingBuildsForArchSet(self._archreleases)

        for build in builds:
            if not build.buildqueue_record:
                name = build.sourcepackagerelease.name
                version = build.sourcepackagerelease.version
                tag = build.distroarchrelease.architecturetag
                self._logger.debug("Creating buildqueue record for %s (%s) "
                                   " on %s" % (name, version, tag))
                build.createBuildQueueEntry()

        self.commit()

    def scanActiveBuilders(self):
        """Collect informations/results of current build jobs."""

        queueItems = getUtility(IBuildQueueSet).getActiveBuildJobs()

        self.getLogger().debug("scanActiveBuilders() found %d active "
                               "build(s) to check" % queueItems.count())

        for job in queueItems:
            proc = job.archrelease.processorfamily
            try:
                builders = notes[proc]["builders"]
            except KeyError:
                continue
            builders.updateBuild(job, self.librarian)
            
    def getLogger(self, subname=None):
        """Return the logger instance with specific prefix"""
        if subname is None:
            return self._logger

        return logging.getLogger("%s.%s" % (self._logger.name, subname))

    def scoreBuildQueueEntry(self, job, now=None):
        """Score Build Job according several fields

        Generate a Score index according some job properties:
        * distribution release component
        * sourcepackagerelease urgency
        """
        if now is None:
            now = datetime.datetime.now(pytz.timezone('UTC'))
            
        if job.manual:
            self._logger.debug("%s (%d) MANUALLY RESCORED"
                               % (job.name, job.lastscore))
            return

        score = 0
        score_componentname = {
            'multiverse': 0,
            'universe': 250,
            'restricted': 750,
            'main': 1000,
            }

        score_urgency = {
            dbschema.SourcePackageUrgency.LOW: 5,
            dbschema.SourcePackageUrgency.MEDIUM: 10,
            dbschema.SourcePackageUrgency.HIGH: 15,
            dbschema.SourcePackageUrgency.EMERGENCY: 20,
            }

        # Define a table we'll use to calculate the score based on the time
        # in the build queue.  The table is a sorted list of (upper time
        # limit in seconds, score) tuples.
        queue_time_scores = [
            (14400, 100),
            (7200, 50),
            (3600, 20),
            (1800, 15),
            (900, 10),
            (300, 5),
        ]

        score = 0
        msg = "%s (%d) -> " % (job.build.title, job.lastscore)

        # Calculate the urgency-related part of the score
        score += score_urgency[job.urgency]
        msg += "U+%d " % score_urgency[job.urgency]

        # Calculate the component-related part of the score
        score += score_componentname[job.component_name]
        msg += "C+%d " % score_componentname[job.component_name]

        # Calculate the build queue time component of the score
        eta = now - job.created
        for limit, dep_score in queue_time_scores:
            if eta.seconds > limit:
                score += dep_score
                msg += "%d " % score
                break

        # Score the package down if it has unsatisfiable build-depends
        # in the hope that doing so will allow the depended on package
        # to be built first.
        if job.builddependsindep:
            depindep_score, missing_deps = self._scoreAndCheckDependencies(
                job.builddependsindep, job.archrelease)
            # sum dependency score
            score += depindep_score

        # store current score value
        job.lastscore = score
        self._logger.debug(msg + " = %d" % job.lastscore)

    def _scoreAndCheckDependencies(self, dependencies_line, archrelease):
        """Check dependencies line within a distroarchrelease.

        Return tuple containing the designed score points related to
        satisfied/unsatisfied dependencies and a line containing the
        missing dependencies in the default dependency format.
        """
        # parse package build dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.ParseDepends(dependencies_line)
        except (ValueError, TypeError):
            self._logger.critical("COULD NOT PARSE DEP: %s" %
                                  dependencies_line)
            # XXX cprov 20051018:
            # We should remove the job if we could not parse its
            # dependency, but AFAICS, the integrity checks in
            # uploader component will be in charge of this. In
            # short I'm confident this piece of code is never
            # going to be executed
            return 0, dependencies_line

        missing_deps = []
        score = 0

        for token in parsed_deps:
            # XXX cprov 20060227: it may not work for and'd and or'd
            # syntaxes.
            try:
                name, version, relation = token[0]
            except ValueError:
                # XXX cprov 20051018:
                # We should remove the job if we could not parse its
                # dependency, but AFAICS, the integrity checks in
                # uploader component will be in charge of this. In
                # short I'm confident this piece of code is never
                # going to be executed
                self._logger.critical("DEP FORMAT ERROR: '%s'" % token[0])
                return 0, dependencies_line

            dep_candidate = archrelease.findDepCandidateByName(name)

            if dep_candidate:
                # use apt_pkg function to compare versions
                # it behaves similar to cmp, i.e. returns negative
                # if first < second, zero if first == second and
                # positive if first > second
                dep_result = apt_pkg.VersionCompare(
                    dep_candidate.binarypackageversion, version)
                # use the previously mapped result to identify whether
                # or not the dependency was satisfied or not
                if version_relation_map[relation](dep_result):
                    # continue for satisfied dependency
                    score -= SCORE_SATISFIEDDEP
                    continue

            # append missing token
            self._logger.warn("MISSING DEP: %r in %s %s"
                              % (token, archrelease.distrorelease.name,
                                 archrelease.architecturetag))
            missing_deps.append(token)
            score -= SCORE_UNSATISFIEDDEP

        # rebuild dependencies line
        remaining_deps = []
        for token in missing_deps:
            name, version, relation = token[0]
            if relation and version:
                token_str = '%s (%s %s)' % (name, relation, version)
            else:
                token_str = '%s' % name
            remaining_deps.append(token_str)

        return score, ", ".join(remaining_deps)

    def retryDepWaiting(self):
        """Check 'dependency waiting' builds and see if we can retry them.

        Check 'dependencies' field and update its contents. Retry those with
        empty dependencies.
        """
        # Get the missing dependency fields
        arch_ids = [arch.id for arch in self._archreleases]
        status = dbschema.BuildStatus.MANUALDEPWAIT
        bqset = getUtility(IBuildSet)
        candidates = bqset.getBuildsByArchIds(arch_ids, status=status)
        # XXX cprov 20060227: IBuildSet.getBuildsByArch API is evil,
        # we should always return an SelectResult, even for empty results
        if candidates is None:
            self._logger.info("No MANUALDEPWAIT record found")
            return

        self._logger.info(
            "Found %d builds in MANUALDEPWAIT state. Checking:"
            % candidates.count())

        for build in candidates:
            # XXX cprov 20060606: This iteration/check should be provided
            # by IBuild.

            if not build.distrorelease.canUploadToPocket(build.pocket):
                # skip retries for not allowed in distrorelease/pocket
                self._logger.debug('SKIPPED: %s can not build in %s/%s'
                                   % (build.title, build.distrorelease.name,
                                      build.pocket.name))
                continue

            if build.dependencies:
                dep_score, remaining_deps = self._scoreAndCheckDependencies(
                    build.dependencies, build.distroarchrelease)
                # store new missing dependencies
                build.dependencies = remaining_deps
                if len(build.dependencies):
                    self._logger.debug(
                        'WAITING: %s "%s"' % (build.title, build.dependencies))
                    continue

            # retry build if missing dependencies is empty
            self._logger.debug('RETRY: "%s"' % build.title)
            build.retry()

        self.commit()

    def sanitiseAndScoreCandidates(self):
        """Iter over the buildqueue entries sanitising it."""
        # Get the current build job candidates
        state = dbschema.BuildStatus.NEEDSBUILD
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(self._archreleases, state)
        self._logger.info("Found %d build in NEEDSBUILD state. Rescoring"
                          % candidates.count())

        # 1. Remove any for which there are no files (shouldn't happen but
        # worth checking for)
        jobs = []
        for job in candidates:
            if job.files:
                jobs.append(job)
                self.scoreBuildQueueEntry(job)
            else:
                distro = job.archrelease.distrorelease.distribution
                distrorelease = job.archrelease.distrorelease
                archtag = job.archrelease.architecturetag
                # remove this entry from the database.
                job.destroySelf()
                self._logger.debug("Eliminating build of %s/%s/%s/%s/%s due "
                                   "to lack of source files"
                                   % (distro.name, distrorelease.name,
                                      archtag, job.name, job.version))
            # commit every cycle to ensure it won't be lost.
            self.commit()

        self._logger.info("After paring out any builds for which we "
                           "lack source, %d NEEDSBUILD" % len(jobs))

        # And finally return that list
        return jobs

    def sortByScore(self, queueItems):
        """Sort queueItems by lastscore, in descending order."""
        queueItems.sort(key=lambda x: x.lastscore, reverse=True)

    def sortAndSplitByProcessor(self):
        """Split out each build by the processor it is to be built for then
        order each sublist by its score. Get the current build job candidates
        """
        state = dbschema.BuildStatus.NEEDSBUILD
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(self._archreleases, state)
        self._logger.debug("Found %d NEEDSBUILD" % candidates.count())


        result = {}

        for job in candidates:
            job_proc = job.archrelease.processorfamily
            result.setdefault(job_proc, []).append(job)

        for job_proc in result:
            self.sortByScore(result[job_proc])

        return result

    def dispatchByProcessor(self, proc, queueItems):
        """Dispatch Jobs according specific processor"""
        self.getLogger().debug("dispatchByProcessor(%s, %d queueItem(s))"
                               % (proc.name, len(queueItems)))
        try:
            builders = notes[proc]["builders"]
        except KeyError:
            self._logger.debug("No builder found.")
            return

        builder = builders.firstAvailable()

        while builder is not None and len(queueItems) > 0:
            build_candidate = queueItems.pop(0)
            spr = build_candidate.build.sourcepackagerelease
            # either dispatch or mark obsolete builds (sources superseded
            # or removed) as SUPERSEDED.
            if (spr.publishings and spr.publishings[0].status <=
                dbschema.PackagePublishingStatus.PUBLISHED):
                self.startBuild(builders, builder, build_candidate)
                builder = builders.firstAvailable()
            else:
                self._logger.debug(
                    "Build %s SUPERSEDED, queue item %s REMOVED"
                    % (build_candidate.build.id, build_candidate.id))
                build_candidate.build.buildstate = (
                    dbschema.BuildStatus.SUPERSEDED)
                build_candidate.destroySelf()


    def startBuild(self, builders, builder, queueItem):
        """Find the list of files and give them to the builder."""
        pocket = queueItem.build.pocket

        self.getLogger().debug("startBuild(%s, %s, %s, %s)"
                               % (builder.url, queueItem.name,
                                  queueItem.version, pocket.title))

        # ensure build has the need chroot
        chroot = queueItem.archrelease.getChroot(pocket)
        if chroot is None:
            self.getLogger().warn(
                "Missing CHROOT for %s/%s/%s/%s"
                % (queueItem.build.distrorelease.distribution.name,
                   queueItem.build.distrorelease.name,
                   queueItem.build.distroarchrelease.architecturetag,
                   queueItem.build.pocket.name))
            return

        try:
            # send chroot
            builders.giveToBuilder(builder, chroot, self.librarian)
            # build filemap structure with the files required in this build.
            # and send them to the builder.
            filemap = {}
            for f in queueItem.files:
                fname = f.libraryfile.filename
                filemap[fname] = f.libraryfile.content.sha1
                builders.giveToBuilder(builder, f.libraryfile, self.librarian)
            # build extra arguments
            args = {
                "ogrecomponent": queueItem.component_name,
                }
            # turn 'arch_indep' ON only if build is archindep or if
            # the specific architecture is the nominatedarchindep for
            # this distrorelease (in case it requires any archindep source)
            args['arch_indep'] = (queueItem.archhintlist == 'all' or
                                  queueItem.archrelease.isNominatedArchIndep)
            # request start of the process
            builders.startBuild(builder, queueItem, filemap,
                                "debian", pocket, args)
        except (xmlrpclib.Fault, socket.error), info:
            # mark builder as 'failed'.
            self._logger.warn("Disabling builder: %s" % builder.url,
                              exc_info=1)
            builders.failBuilder(
                builder, "Exception (%s) when setting up to new job" % info)

        self.commit()

