# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Master implementation

# 17:53 < kiko> first a "The Shining" DVD
# 17:53 < kiko> second a set of COMPUTING-related books
# 17:53 < kiko> then
# 17:53 < kiko> he's finally ready for his encounter with Fiera

from canonical.lp import initZopeless
from canonical.launchpad.database import Builder, BuildQueue, Build, \
     Distribution, DistroRelease, DistroArchRelease
from canonical.librarian.client import FileUploadClient, FileDownloadClient
from canonical.buildd.utils import notes
from sets import Set
import logging
import xmlrpclib
import os
from base64 import standard_b64encode as base64encode
from base64 import standard_b64decode as base64decode

class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class BuilderSet:
    """Manage a set of builders based on a given architecture"""

    def __init__(self, architecture, logger, archtag):
        self.logger = logger
        self.arch = architecture
        self.archtag = archtag
        self.builders = Builder.select("""builder.processor = processor.id
                                          AND
                                          processor.family = %d
        """ % self.arch, clauseTables=("Processor",))
        # Actualise the results because otherwise we get our exceptions
        # at odd times
        self.logger.debug("Initialising builders for " + archtag)
        self.builders = Set(self.builders)
        self.logger.debug("Finding XMLRPC clients for the builders")
        for b in self.builders:
            if not b.builderok:
                continue
            n = notes[b]
            if not "slave" in n:
                n["slave"] = xmlrpclib.Server("http://%s:8221/" % b.fqdn)
            try:
                if n["slave"].echo("Test")[0] != "Test":
                    raise ValueError, "Failed to echo OK"
                (vers, methods, arch, mechanisms) = n["slave"].info()
                if vers != 1:
                    raise ValueError, "Protocol version mismatch"
                if arch != self.archtag:
                    raise ValueError, "Architecture tag mismatch: %s != %s" % (arch,self.archtag)
            except Exception, e:
                # Hmm, a problem with the xmlrpc interface, disable the
                # builder
                self.logger.warning("Builder on %s marked as failed due to: %s", (b.fqdn,e))
                b.builderok = False
                b.failnote = "Failure during XMLRPC initialisation: %s" % e

        self.updateOKcount()

    def updateOKcount(self):
        self.okcount=0
        self.okslaves = []
        for b in self.builders:
            if b.builderok:
                self.okcount += 1
                self.okslaves.append((b, notes[b]["slave"]))
        if self.okcount == 0:
            self.logger.debug("No builders are available")

    def failbuilder(self, builder, reason):
        builder.builderok = False
        builder.failnote = reason
        self.updateOKcount()

    def givetobuilder(self, builder, libraryfilealias, librarian):
        if not builder.builderok:
            raise BuildDaemonError, "Attempted to give a file to a known-bad builder"
        s = notes[builder]["slave"]
        if not s.doyouhave(libraryfilealias.content.sha1):
            self.logger.debug("Attempting to fetch %s to give to builder on %s" % (libraryfilealias.content.sha1, builder.fqdn))
            # 1. Get the file download object going
            ## XXX: This fails because the URL gets unescaped?
            d = librarian.getFileByAlias(libraryfilealias.id)
            fc = base64encode(d.read())
            d.close()
            # 2. Give the file to the remote end.
            self.logger.debug("Passing it on...")
            storedsum = s.storefile(fc)
            if storedsum != libraryfilealias.content.sha1:
                raise BuildDaemonError, "Storing to buildd slave failed, %s != %s" % (storedsum, libraryfilealias.content.sha1)
        

class BuilddMaster:
    """Canonical autobuilder master, toolkit and algorithms"""

    def __init__(self, logger):
        self._logger = logger
        self._logger.debug("Initialising ZTM")
        self._tm = initZopeless()
        self._dars = {}

        self._logger.info("Buildd Master has been initialised")

    def commit(self):
        self._tm.commit()

    def rollback(self):
        self._tm.rollback()

    
    def addDistroArchRelease(self, dar):
        # Confirm that the dar can be built
        if dar.chroot is None:
            raise ValueError, dar
        self._logger.info("Adding DistroArchRelease %s/%s/%s" % (dar.distrorelease.distribution.name, dar.distrorelease.name, dar.architecturetag))
        # Fill out the contents
        self._dars.setdefault(dar, {})
        # Determine the builders for this distroarchrelease...
        sentinel = object()
        builders = self._dars[dar].setdefault("builders", sentinel)
        if builders is sentinel:
            if 'builders' not in notes[dar.processorfamily]:
                notes[dar.processorfamily]["builders"] = \
                        BuilderSet(dar.processorfamily.id, \
                                   self.getLogger("builders." + dar.processorfamily.name), dar.architecturetag)                               
            self._dars[dar]["builders"] = notes[dar.processorfamily]["builders"]
            builders = self._dars[dar]["builders"]
                        
        # Count the available builders
        if builders.okcount == 0:
            del self._dars[dar]
            raise BuildDaemonError, "No builders found for this distroarchrelease"
        # Ensure that each builder has the chroot for this dar
        self.uselessbuilders = Set()
        for b,s in builders.okslaves:
            try:
                builders.givetobuilder(b, dar.chroot, self.downloader)
            except Exception, e:
                self._logger.warn("Disabling builder: %s" % b.fqdn, exc_info=1)
                builders.failbuilder(b, "Exception %s passing a chroot to the builder" % e)

    def getLogger(self, subname=None):
        if subname is None:
            return self._logger
        l = logging.getLogger("%s.%s" % (self._logger.name, subname))
        return l

    def setUploader(self, uploader):
        self.uploader = uploader

    def setDownloader(self, downloader):
        self.downloader = downloader


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().debug("Initialising buildd master")
    bm = BuilddMaster(logging.getLogger('buildd'))
    librarian_host = os.environ.get('LB_HOST', 'localhost')
    librarian_port = int(os.environ.get('LB_DPORT', '8000'))


    downloader = FileDownloadClient(librarian_host, librarian_port)

    bm.setDownloader(downloader)

    librarian_port = int(os.environ.get('LB_UPORT', '9090'))
    uploader = FileUploadClient();
    uploader.connect(librarian_host, librarian_port)

    bm.setUploader(uploader)
    
    # For every distroarchrelease we can find; put it into the build master
    for dar in DistroArchRelease.select():
        try:
            bm.addDistroArchRelease(dar)
        except Exception, e:
            logging.getLogger().warn("Unable to add %s/%s/%s to buildd" % (
                dar.distrorelease.distribution.name, dar.distrorelease.name,
                dar.architecturetag), exc_info=1)

    # Now that the dars are added, ask the buildmaster to calculate the set
    # of build candiates
    # XXX: dsilvers 2005-02-05 write this
    # bm.calculateCandidates()
