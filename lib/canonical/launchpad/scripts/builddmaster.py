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
import warnings
import xmlrpclib
import socket
from cStringIO import StringIO
import datetime
import pytz
import tempfile
import os
import apt_pkg
import subprocess
import shutil

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from sqlobject import SQLObjectNotFound

from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.interfaces import (
    IBuilderSet, IBuildQueueSet, IBuildSet, ILibraryFileAliasSet,
    IBinaryPackageReleaseSet, IBinaryPackageNameSet
    )

from canonical.lp import dbschema
from canonical import encoding
from canonical.database.constants import UTC_NOW
from canonical.launchpad.helpers import filenameToContentType

from canonical.buildd.slave import BuilderStatus
from canonical.buildd.utils import notes


KBYTE=1024
def file_chunks(from_file, chunk_size=256*KBYTE):
    """Using the special two-arg form of iter() iterate a file's chunks."""
    return iter(lambda: from_file.read(chunk_size), '')

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

    def rollback(self):
        self._tm.rollback()

    def __init__(self, logger, tm, upload_cmdline):
        self._tm = tm
        self.logger = logger
        self.upload_cmdline = upload_cmdline

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
        
        Check id builder is working properly, build the librarian URL
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

        if not slave.ensurepresent(libraryfilealias.content.sha1, url):
            raise BuildDaemonError(
                "Build slave was unable to fetch from %s" % url)
        
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
        buildid = "%s-%s" % (queueItem.build.id, queueItem.id)
        self.logger.debug("Initiating build %s on %s"
                          % (buildid, builder.url))

        chroot = self.findChrootFor(queueItem, pocket)
        if not chroot:
            self.logger.critical("OOPS! Could not find CHROOT")
            return

        queueItem.builder = builder
        queueItem.buildstart = UTC_NOW

        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(builder.slave)

        slave.build(buildid, buildtype, chroot, filemap, args)

    def getLogFromSlave(self, slave, buildid, librarian):
        """Get last buildlog from slave.

        Invoke getFileFromSlave method with 'buildlog' identifier.
        """
        return self.getFileFromSlave(slave, "log-for-%s.txt" % buildid,
                                     'buildlog', librarian)

    def getFileFromSlave(self, slave, filename, sha1sum, librarian):
        """Request a file from Slave.

        Protocol version 1.0new or higher provides /filecache/
        which allows us to be clever in large file transfer. This method
        Receive a file identifier (sha1sum) a MIME header filename and a
        librarian instance. Store the incomming file in Librarian and return
        the file alias_id, if it failed return None. 'buildlog' string is a
        special indentifier which recover the raw last slave buildlog, 
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
                out_file.seek(0,2)
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
        # build the slave build job id key
        buildid = "%s-%s" % (queueItem.build.id, queueItem.id)

        # XXX cprov 20051026: Removing annoying Zope Proxy, bug # 3599
        slave = removeSecurityProxy(queueItem.builder.slave)

        try:
            res = slave.status()
        except xmlrpclib.Fault, info:
            # XXX cprov 20050629
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timesamp.
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
        """ABORTING process has succesfully terminated.

        Clean the builder for another jobs.
        """
        # XXX: dsilvers: 20050302: Confirm the builder has the right build?
        queueItem.builder = None
        queueItem.buildstart = None
        slave.clean()

    def updateBuild_WAITING(self, queueItem, slave, librarian, buildstatus,
                            buildid, filemap=None):
        """Perform the actions needed for a slave in a WAITING state

        Buildslave can be WAITING in five situations:

        * Build has failed, no filemap is received (PACKAGEFAIL, DEPFAIL,
                                                    CHROOTFAIL, BUILDERFAIL)
        
        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrive those files and store in
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

        method(queueItem, slave, librarian, buildid, filemap)

    def storeBuildInfo(self, queueItem, slave, librarian, buildid):
        """Store available information for build jobs.

        Store Buildlog, datebuilt, duration and builder signature.
        """
        queueItem.build.buildlog = self.getLogFromSlave(slave, buildid,
                                                        librarian)
        queueItem.build.datebuilt = UTC_NOW
        # we need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        queueItem.build.buildduration = RIGHT_NOW - queueItem.buildstart
        queueItem.build.builder = queueItem.builder
        

    def buildStatus_OK(self, queueItem, slave, librarian, buildid,
                       filemap=None):
        """Builder has built package entirely, get all the content back"""
        self.storeBuildInfo(queueItem, slave, librarian, buildid)
        queueItem.build.buildstate = dbschema.BuildStatus.FULLYBUILT
        # Commit the transaction so that the uploader can see the updated
        # build record 
        self.commit()
        temp_dir = tempfile.mkdtemp(prefix="build-%s" % buildid,
                                    suffix=".upload")

        self.logger.debug("Processing successful build %s in %s" % (
            buildid, temp_dir))
        
        try:
            for filename in filemap:
                slave_file = slave.getFile(filemap[filename])
                out_file_name = os.path.join(temp_dir, filename)
                out_file = open(out_file_name, "wb")
                try:
                    for chunk in file_chunks(slave_file):
                        out_file.write(chunk)
                finally:
                    slave_file.close()
                    out_file.close()

            uploader_argv = list(self.upload_cmdline)
            try:
                while uploader_argv.index("BUILDID"):
                    uploader_argv[uploader_argv.index("BUILDID")] = str(
                        queueItem.build.id)
            except ValueError:
                # Assume this is "not in list" and swallow it
                pass
                
            uploader_argv.append(temp_dir)

            self.logger.debug("Invoking uploader on %s" % temp_dir)
            uploader_process = subprocess.Popen(uploader_argv)
            result_code = uploader_process.wait()
            self.logger.debug("Uploader returned %d" % result_code)
        finally:
            self.logger.debug("Cleaning up temporary directory")
            shutil.rmtree(temp_dir)
        self.logger.debug("Gathered build of %s completely"
                          % queueItem.name)

        # release the builder
        slave.clean()
        queueItem.destroySelf()
        
    def buildStatus_PACKAGEFAIL(self, queueItem, slave, librarian, buildid,
                                filemap=None):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        self.storeBuildInfo(queueItem, slave, librarian, buildid)
        queueItem.build.buildstate = dbschema.BuildStatus.FAILEDTOBUILD
        slave.clean()
        queueItem.destroySelf()
        
    def buildStatus_DEPFAIL(self, queueItem, slave, librarian, buildid,
                            filemap=None):
        """Handle a package that had missed dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store availble information, remove BuildQueue
        entry and release builder slave for another job.
        """
        self.storeBuildInfo(queueItem, slave, librarian, buildid)
        queueItem.build.buildstate = dbschema.BuildStatus.MANUALDEPWAIT
        self.logger.critical("***** %s is MANUALDEPWAIT *****"
                             % queueItem.builder.name)
        slave.clean()
        queueItem.destroySelf()
        
    def buildStatus_CHROOTFAIL(self, queueItem, slave, librarian, buildid,
                               filemap=None):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        self.storeBuildInfo(queueItem, slave, librarian, buildid)
        queueItem.build.buildstate = dbschema.BuildStatus.CHROOTWAIT
        self.logger.critical("***** %s is CHROOTWAIT *****" %
                             queueItem.builder.name)
        slave.clean()
        queueItem.destroySelf()
                
    def buildStatus_BUILDERFAIL(self, queueItem, slave, librarian, buildid,
                                filemap=None):
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
                except Exception, e:
                    self.logger.debug("Builder %s wasn't counted due to (%s)."
                                      % (builder.url, e))
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
                except Exception, e:
                    continue
                if slavestatus[0] == BuilderStatus.IDLE:
                    return builder
        return


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
    def __init__(self, logger, tm, upload_cmdline):
        self._logger = logger
        self._tm = tm
        self.librarian = getUtility(ILibrarianClient)
        self._archreleases = {}
        self.upload_cmdline = upload_cmdline
        self._logger.info("Buildd Master has been initialised")
        
    def commit(self):
        self._tm.commit()

    def rollback(self):
        self._tm.rollback()

    def addDistroArchRelease(self, archrelease, pocket=None):        
        """Setting up a workable DistroArchRelease for this session."""
        # ensure we have a pocket
        if not pocket:
            pocket = dbschema.PackagePublishingPocket.RELEASE

        self._logger.info("Adding DistroArchRelease %s/%s/%s/%s"
                          % (archrelease.distrorelease.distribution.name,
                             archrelease.distrorelease.name,
                             archrelease.architecturetag, pocket))
        # ensure ARCHRELEASE has a pocket
        if not archrelease.getChroot(pocket):
            self._logger.warn("Disabling: No CHROOT found for %s pocket '%s'"
                              % (archrelease.title, pocket.title))
            return
        
        # Fill out the contents
        self._archreleases.setdefault(archrelease, {})
    
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
            builderGroup = BuilderGroup(self.getLogger(info), self._tm,
                                        self.upload_cmdline)
            
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
        # 1. get all sourcepackagereleases published or pending in this
        # distrorelease        
        spp = distrorelease.getAllReleasesByStatus(
            dbschema.PackagePublishingStatus.PUBLISHED
            )
        
        self._logger.info("Scanning publishing records for %s/%s...",
                          distrorelease.distribution.title,
                          distrorelease.title)

        releases = set(pubrec.sourcepackagerelease for pubrec in spp)

        self._logger.info("Found %d Sources to build.", len(releases))
        
        # Do not create builds for distroreleases with no nominatedarchindep
        # they can't build architecture independent packages properly.
        if not distrorelease.nominatedarchindep:
            self._logger.warn("No Nominated Architecture Independent, skipping"
                              " distrorelease %s", distrorelease.title)
            return

        # 2. Determine the set of distroarchreleases we care about in this
        # cycle
        archs = set(arch for arch in distrorelease.architectures
                    if arch in self._archreleases)

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
        for release in releases:
            header = ("Build Record %s-%s for '%s' " %
                      (release.name, release.version,
                       release.architecturehintlist))

            # Abort packages with empty architecturehintlist, they are simply
            # wrong.
            # XXX cprov 20050931
            # This check should be done earlier in the upload component/hct
            if release.architecturehintlist is None:
                self._logger.debug(header + "ABORT EMPTY ARCHHINTLIST")
                continue

            # Verify if the sourcepackagerelease build in ALL arch
            # in this case only one build entry is needed.
            if release.architecturehintlist == "all":

                # it's already there, skip to next package
                if release.builds:
                    self._logger.debug(header + "SKIPPING ALL")
                    continue
                
                # packages with an architecture hint of "all" are
                # architecture independent.  Therefore we only need
                # to build on one architecture, the distrorelease.
                # nominatedarchindep
                processor = distrorelease.nominatedarchindep.default_processor
                release.createBuild(
                    distroarchrelease=distrorelease.nominatedarchindep,
                    processor=processor)
                self._logger.debug(header + "CREATING ALL")
                continue

            # the sourcepackage release builds in a specific list of
            # architetures or in ANY.
            # it should be cross-combined with the current supported
            # architetures in this distrorelease.
            for arch in archs:
                # if the sourcepackagerelease doesn't build in ANY
                # architecture and the current architecture is not
                # mentioned in the list, continues 
                supported = release.architecturehintlist.split()
                if ('any' not in supported and arch.architecturetag not in
                    supported):
                    self._logger.debug(header + "NOT SUPPORTED %s" %
                                       arch.architecturetag)
                    continue
                
                # verify is isn't already present for this distroarchrelease
                if not release.getBuildByArch(arch):
                    # XXX cprov 20050831
                    # I could possibily be better designed, let's think about
                    # it in the future. Pick the first processor we found for
                    # this distroarchrelease.processorfamily. The data model
                    # should change to have a default processor for a
                    # processorfamily 
                    release.createBuild(distroarchrelease=arch,
                                        processor=arch.default_processor)

                    self._logger.debug(header + "CREATING %s" %
                                       arch.architecturetag)
                else:
                    self._logger.debug(header + "SKIPPING %s" %
                                       arch.architecturetag)
        self.commit()

    def addMissingBuildQueueEntries(self):
        """Create missed Buiild Jobs. """
        self._logger.debug("Scanning for build queue entries that are missing")
        # Get all builds in NEEDSBUILD which are for a distroarchrelease
        # that we build...
        if not self._archreleases:
            self._logger.debug("No DistroArchrelease Initialized")
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

    def scoreBuildQueueEntry(self, job):
        """Score Build Job according several fields
        
        Generate a Score index according some job properties:
        * distribution release component
        * sourcepackagerelease urgency
        """        
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
        msg = "%s (%d) -> " % (job.name, job.lastscore)
        
        # Calculate the urgency-related part of the score
        score += score_urgency[job.urgency]
        msg += "U+%d " % score_urgency[job.urgency]
        
        # Calculate the component-related part of the score
        score += score_componentname[job.component_name]
        msg += "C+%d " % score_componentname[job.component_name]

        # Calculate the build queue time component of the score
        eta = datetime.datetime.now(pytz.timezone('UTC')) - job.created
        for limit, dep_score in queue_time_scores:
            if eta.seconds > limit:
                score += dep_score
                msg += "%d " % score
                break

        # parse package builde dependencies using apt_pkg
        try:
            parsed_deps = apt_pkg.ParseDepends(job.builddependsindep)
        except ValueError:
            self._logger.warn("COULD NOT PARSE DEP: %s" %
                              job.builddependsindep)
            parsed_deps = []
            
        # apt_pkg requires InitSystem to get VersionCompare working properly
        apt_pkg.InitSystem()

        # this dict maps the package version relationship syntax in lambda
        # functions which returns bollean according the results of
        # apt_pkg.VersionCompare function (see the order above).
        # For further information about pkg relationship syntax see:
        #
        # http://www.debian.org/doc/debian-policy/ch-relationships.html
        #
        relation_map = {
            # any version is acceptable if no relationship is given
            '': lambda x : True,
            # stricly later
            '>>': lambda x : x == 1,
            # later or equal
            '>=': lambda x : x >= 0,
            # stricly equal
            '=': lambda x : x == 0,
            # earlier or equal
            '<=': lambda x : x <= 0,
            # strictly ealier
            '<<': lambda x : x == -1
            }

        for token in parsed_deps:
            try:
                name, version, relation = token[0]
            except ValueError:
                # XXX cprov 20051018:
                # We should remove the job if we could not parse it's
                # dependency, but AFAICS, the integrity checks in uploader
                # component will be in charge of this. In few words i'm
                # confident this piece of code are never going to be executed
                self._logger.critical("DEP FORMAT ERROR: '%s'" % token[0])
                continue
            
            dep_candidate = job.archrelease.findDepCandidateByName(name)
            
            if dep_candidate:
                # use apt_pkg function to compare versions
                # it behaves similar to cmp, i.e., returns negative
                # if first < second, zero if first == second and
                # positive if first > second
                dep_result = apt_pkg.VersionCompare(
                    dep_candidate.binarypackageversion, version)

                # use the previous mapped result to identify if the depency
                # ws satisfied or not
                if relation_map[relation](dep_result):
                    # grant more 1 (one) point of scoring for each satisfied
                    # dependency
                    score += 1
                    continue
                
            # reduce score in 10 point for each unsatisfied dependency
            score -= 10
            self._logger.warn("MISSED DEP: %r in %s %s"
                              % (token, job.archrelease.distrorelease.name,
                                 job.archrelease.architecturetag))
            
        # store current score value
        job.lastscore = score
        self._logger.debug(msg + " = %d" % job.lastscore)

    def sanitiseAndScoreCandidates(self):
        """Iter over the buildqueue entries sanitising it."""
        # Get the current build job candidates
        state = dbschema.BuildStatus.NEEDSBUILD
        bqset = getUtility(IBuildQueueSet)
        candidates = bqset.calculateCandidates(self._archreleases, state)
        self._logger.debug("Found %d NEEDSBUILD" % candidates.count())

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
            
        self._logger.debug("After paring out any builds for which we "
                           "lack source, %d NEEDSBUILD" % len(jobs))
        
        # And finally return that list        
        return jobs

    def sortByScore(self, queueItems):
        queueItems.sort(key=lambda x: x.lastscore)

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

    def dispatchByProcessor(self, proc, queueItems, pocket=None):
        """Dispach Jobs according specific procesor and pocket """
        # ensure we have a pocket
        if not pocket:
            pocket = dbschema.PackagePublishingPocket.RELEASE
        
        self.getLogger().debug("dispatchByProcessor(%s, %d queueItem(s), %s)"
                               % (proc.name, len(queueItems), pocket.title))
        builders = notes[proc]["builders"]
        builder = builders.firstAvailable()

        while builder is not None and len(queueItems) > 0:
            self.startBuild(builders, builder, queueItems.pop(0), pocket)
            builder = builders.firstAvailable()                

    def startBuild(self, builders, builder, queueItem, pocket):
        """Find the list of files and give them to the builder."""

        build = queueItem.build
        
        self.getLogger().debug("startBuild(%s, %s, %s, %s)"
                               % (builder.url, queueItem.name,
                                  queueItem.version, pocket.title))

        # ensure build has the need chroot
        chroot = queueItem.archrelease.getChroot(pocket)

        try:
            builders.giveToBuilder(builder, chroot, self.librarian)
        except Exception, e:
            self._logger.warn("Disabling builder: %s" % builder.url,
                              exc_info=1)
            builders.failBuilder(builder, ("Exception %s passing a chroot "
                                           "to the builder" % e))
        else:
            filemap = {}
            
            for f in queueItem.files:
                fname = f.libraryfile.filename
                filemap[fname] = f.libraryfile.content.sha1
                builders.giveToBuilder(builder, f.libraryfile, self.librarian)

            args = {
                "ogrecomponent": queueItem.component_name,
                }
            # turn 'arch_indep' ON only if build is archindep or if
            # the specific architecture is the nominatedarchindep for
            # this distrorelease (in case it requires any archindep source)
            args['arch_indep'] = (queueItem.archhintlist == 'all' or
                                  queueItem.archrelease.isNominatedArchIndep)
                
            builders.startBuild(builder, queueItem, filemap,
                                "debian", pocket, args)
        self.commit()
