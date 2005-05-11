# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Master implementation

# 17:53 < kiko> first a "The Shining" DVD
# 17:53 < kiko> second a set of COMPUTING-related books
# 17:53 < kiko> then
# 17:53 < kiko> he's finally ready for his encounter with Fiera

from canonical.lp import initZopeless
from canonical.launchpad.database import Builder, BuildQueue, Build,          \
     Distribution, DistroRelease, DistroArchRelease, SourcePackagePublishing, \
     LibraryFileAlias, BinaryPackage, BinaryPackageFile, BinaryPackageName, \
     SourcePackageReleaseFile
from canonical.librarian.client import FileUploadClient, FileDownloadClient
from canonical.buildd.utils import notes
from canonical.lp.dbschema import PackagePublishingStatus, \
     BuildStatus as DBBuildStatus,       \
     BinaryPackageFormat, BinaryPackageFileType
from canonical.database.constants import nowUTC
from canonical.buildd.slave import BuilderStatus, BuildStatus
from sets import Set
from StringIO import StringIO
import logging
import xmlrpclib
import os

# This is pretty much only used in debug output
def y(cond,truth,falsehood):
    """Think: ternary operator."""
    if cond:
        return truth
    return falsehood

# This should go away when we move to doing proper uploads.
def filenameToContentType(fname):
    ftmap = {
    ".dsc":"text/plain",
    ".changes":"text/plain",
    ".deb":"application/x-debian-package",
    ".udeb":"application/x-debian-package",
    }
    for ending in ftmap:
        if fname.endswith(ending):
            return ftmap[ending]
    return "application/octet-stream"

class BuildDaemonError(Exception):
    """The class of errors raised by the buildd classes"""


class BuilderGroup:
    """Manage a set of builders based on a given architecture"""

    def commit(self):
        self._tm.commit()

    def rollback(self):
        self._tm.rollback()

    def __init__(self, architecture, logger, archtag, tm):
        self._tm = tm
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
            self.logger.debug("They're all dead. Everybody's dead, Dave.")
            self.logger.warn("No builders are available")

    def failbuilder(self, builder, reason):
        builder.builderok = False
        builder.failnote = reason
        self.updateOKcount()

    def givetobuilder(self, builder, libraryfilealias, librarian):
        if not builder.builderok:
            raise BuildDaemonError, "Attempted to give a file to a known-bad builder"
        s = notes[builder]["slave"]
        self.logger.debug("Asking builder on %s if it has file %s (%s)" % (builder.fqdn, libraryfilealias.filename, libraryfilealias.content.sha1))
        if not s.doyouhave(libraryfilealias.content.sha1, libraryfilealias.id):
            self.logger.debug("Attempting to fetch %s to give to builder on %s" % (libraryfilealias.content.sha1, builder.fqdn))
            # 1. Get the file download object going
            ## XXX: This fails because the URL gets unescaped?
            d = librarian.getFileByAlias(libraryfilealias.id)
            fc = xmlrpclib.Binary(d.read())
            d.close()
            # 2. Give the file to the remote end.
            self.logger.debug("Passing it on...")
            storedsum = s.storefile(fc)
            if storedsum != libraryfilealias.content.sha1:
                raise BuildDaemonError, "Storing to buildd slave failed, %s != %s" % (storedsum, libraryfilealias.content.sha1)
        else:
            self.logger.debug("It does")

    def findchrootfor(self, qitem):
        dar = qitem.build.distroarchrelease
        chroot = dar.chroot
        return chroot.content.sha1

    def startBuild(self, builder, qitem, filemap, buildtype):
        buildid = "%s-%s" % (qitem.build.id, qitem.id)
        self.logger.debug("Initiating build %s on %s" % (buildid, builder.fqdn))
        s = notes[builder]["slave"]
        qitem.builder = builder
        qitem.buildstart = nowUTC
        s.startbuild(buildid, filemap, self.findchrootfor(qitem), buildtype)

    def getLogFromSlave(self, slave, buildid, uploader):
        log = slave.fetchlogtail(-1)
        sio = StringIO(log)
        fileid,aliasid = uploader.addFile("log-for-%s" % buildid,
                                          len(log), sio,
                                          contentType="text/plain");
        # XXX: dsilvers: 20050302: Remove these when the library works
        self.commit()
        return aliasid

    def getFileFromSlave(self, slave, filename, sha1sum, uploader):
        b = slave.fetchfile(sha1sum)
        s = b.__str__()
        sio = StringIO(s)
        fileid, aliasid = uploader.addFile(filename,
                                           len(s), sio,
                                           contentType=filenameToContentType(filename))
        # XXX: dsilvers: 20050302: Remove these when the library works
        self.commit()
        return aliasid

    def getBinaryPackageName(self, bpname):
        bn = BinaryPackageName.selectBy(name=bpname)
        if bn.count() == 0:
            bn = [BinaryPackageName(name=bpname)]
        return bn[0]

    def processBinaryPackage(self, build, aliasid, filename):
        alias = LibraryFileAlias.get(aliasid)
        # at_3.1.8-11ubuntu2_i386.deb
        bpname = filename[:filename.find("_")]
        filename2 = filename[filename.find("_")+1:]
        version = filename2[:filename2.find("_")]
        archdep = True
        if filename.endswith("all.deb"):
            archdep = False
        bpname = self.getBinaryPackageName(bpname)
        bp = BinaryPackage(
            binarypackagename = bpname,
            version = version,
            shortdesc="",
            description="",
            build = build,
            binpackageformat = BinaryPackageFormat.DEB,
            component = 1, # XXX: dsilvers: 20050302: This needs filling out
            section = 1, #XXX: as above
            architecturespecific = archdep,
            priority = None,
            shlibdeps = None,
            depends = None,
            recommends = None,
            suggests = None,
            conflicts = None,
            replaces = None,
            provides = None,
            essential = None,
            installedsize = None,
            copyright = None,
            licence = None,
            )
        bpf = BinaryPackageFile(
            binarypackage = bp,
            libraryfile = alias,
            filetype = BinaryPackageFileType.DEB
            )
        self.logger.debug("Absorbed binary package %s" % filename)
        
    def updateBuild(self, qitem, uploader):
        buildid = "%s-%s" % (qitem.build.id, qitem.id)
        s = notes[qitem.builder]["slave"]
        res = s.status()
        if type(res) != tuple and type(res) != list:
            res = (res,)

        if res[0] == BuilderStatus.IDLE:
            # Somehow the builder forgot about the build
            # log this and reset the record
            self.logger.warn("Builder on %s is Dory AICMFP. Builder forgot about build %s of %s (%s) "
                             "-- resetting buildqueue record" % (
                qitem.builder.fqdn,
                buildid,
                qitem.build.sourcepackagerelease.sourcepackagename.name,
                qitem.build.sourcepackagerelease.version))
            qitem.builder = None
            qitem.buildstart = None
        elif res[0] == BuilderStatus.BUILDING:
            # XXX: dsilvers: 20050302: Confirm the builder has the right build?
            qitem.logtail = res[2]
        elif res[0] == BuilderStatus.WAITING:
            # XXX: dsilvers: 20050302: Confirm the builder has the right build?
            qitem.build.buildlog = self.getLogFromSlave(s,
                                                        buildid,
                                                        uploader)
            qitem.build.datebuilt = nowUTC
            if res[1] == BuildStatus.OK:
                # Builder has built package entirely, get all the content back
                qitem.build.builder = qitem.builder
                #XXX: dsilvers: 20050302: How do I get an interval for here?
                #qitem.build.buildduration = qitem.buildstart
                qitem.build.buildstate = DBBuildStatus.FULLYBUILT
                filemap = res[3]
                for f in filemap:
                    aliasid = self.getFileFromSlave(s, f, filemap[f], uploader)
                    if f.endswith(".deb"):
                        # Process a binary package
                        self.processBinaryPackage(qitem.build, aliasid, f)
                self.logger.debug("Gathered build of %s completely" % qitem.build.sourcepackagerelease.sourcepackagename.name)
            elif res[1] == BuildStatus.DEPFAIL:
                qitem.build.buildstate = DBBuildStatus.MANUALDEPWAIT
            elif res[1] == BuildStatus.PACKAGEFAIL:
                qitem.build.buildstate = DBBuildStatus.FAILEDTOBUILD
            elif res[1] == BuildStatus.CHROOTFAIL:
                qitem.build.buildstate = DBBuildStatus.CHROOTWAIT
            elif res[1] == BuildStatus.BUILDERFAIL:
                qitem.build.buildstate = DBBuildStatus.NEEDSBUILD
                self.failbuilder(qitem.builder, "Builder returned BUILDERFAIL when asked for its status")
            # And reset the builder information
            if qitem.builder.builderok:
                s.clean()
            qitem.builder = None
            qitem.buildstart = None
        elif res[0] == BuilderStatus.ABORTED:
            # XXX: dsilvers: 20050302: Confirm the builder has the right build?
            qitem.builder = None
            qitem.buildstart = None
            s.clean()
        else:
            self.logger.critical("Builder on %s returned unknown status %s, failing it" % (qitem.builder.fqdn, res[0]))
            self.failbuilder(qitem.builder, "Unknown status code (%s) returned from status() probe." % res[0])
            qitem.builder = None
            qitem.buildstart = None
        
    def countAvailable(self):
        c = 0
        for b in self.builders:
            if b.builderok:
                s = notes[b]["slave"]
                ss = s.status()
                if type(ss) == tuple or type(ss) == list:
                    ss = ss[0]
                if ss == BuilderStatus.IDLE:
                    c += 1
        self.logger.debug("Found %d available builder[s]" % c)
        return c

    def firstAvailable(self):
        for b in self.builders:
            if b.builderok:
                s = notes[b]["slave"]
                ss = s.status()
                if type(ss) == tuple or type(ss) == list:
                    ss = ss[0]
                if ss == BuilderStatus.IDLE:
                    return b
        return None


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
                        BuilderGroup(dar.processorfamily.id, \
                                   self.getLogger("builders." + dar.processorfamily.name), dar.architecturetag, self._tm)
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

    def checkForMissingBuilds(self, distrorelease):
        # 1. get all sourcepackagereleases published or pending in this
        # distrorelease
        spp = SourcePackagePublishing.select("""
        distrorelease=%d AND (status=%d OR status=%d)
        """ % (distrorelease.id, PackagePublishingStatus.PENDING.value,
               PackagePublishingStatus.PUBLISHED.value))
        self._logger.debug("Scanning publishing records for %s/%s...", distrorelease.distribution.name, distrorelease.name)
        spr = Set()
        for pubrec in spp:
            spr.add(pubrec.sourcepackagerelease)
        # 2. Determine the set of distroarchreleases we care about in this
        # cycle
        archs = Set()
        for arch in distrorelease.architectures:
            if arch in self._dars:
                archs.add(arch)
        # 3. For each of the sourcepackagereleases, find its builds...
        madesome = False
        for release in spr:
            for arch in archs:
                builds = Build.select("""
                sourcepackagerelease=%d and distroarchrelease=%d
                """ % (release.id, arch.id))
                if builds.count() == 0:
                    self._logger.debug("Creating build record for %s (%s) on %s" % (release.sourcepackagename.name, release.version, arch.architecturetag))
                    # XXX: dsilvers: 21/2/05: processor?! NULL?
                    # Also, what's with having to pass all these None values ?
                    madesome = True
                    b = Build(processor=1,
                              distroarchrelease=arch.id,
                              buildstate=DBBuildStatus.NEEDSBUILD,
                              sourcepackagerelease=release.id,
                              buildduration=None,
                              gpgsigningkey=None,
                              builder=None,
                              buildlog=None,
                              datebuilt=None,
                              changes=None,
                              datecreated=nowUTC
                              )
        if madesome:
            # Missing builds have been created; commit the transaction
            self.commit()

    def addMissingBuildQueueEntries(self):
        self._logger.debug("Scanning for build queue entries that are missing")
        # 1. Get all builds in NEEDSBUILD which are for a distroarchrelease
        # that we build...
        clause = " OR ".join(["distroarchrelease=%d" % d.id for d in self._dars])
        if clause == '':
            clause = "false";
        builds = Build.select("""
        buildstate=%d AND (%s)
        """ % (DBBuildStatus.NEEDSBUILD.value, clause))
        madesome = False
        for b in builds:
            if BuildQueue.selectBy(buildID=b.id).count() == 0:
                madesome = True
                self._logger.debug("Creating buildqueue record for %s (%s) on %s" % (b.sourcepackagerelease.sourcepackagename.name, b.sourcepackagerelease.version, b.distroarchrelease.architecturetag))
                BuildQueue(build = b.id,
                           builder = None,
                           created = nowUTC,
                           buildstart = None,
                           lastscore = None,
                           logtail = None)
        if madesome:
            # Missing build queue entries created; commit the transaction
            self.commit()

    def calculateCandidates(self):
        # Return the candidates for building as a list of buildqueue items
        # which need ordering...
        # 1. determine all buildqueue items which needsbuild
        clause = " OR ".join(["build.distroarchrelease=%d" % d.id for d in self._dars])
        if clause == '':
            clause = "false";
        q1 = BuildQueue.select("""
        buildqueue.build = build.id AND
        build.buildstate = %d AND
        buildqueue.builder IS NULL AND
        (%s)
        """ % (DBBuildStatus.NEEDSBUILD.value, clause), clauseTables=['Build'])
        self._logger.debug("Found %d NEEDSBUILD" % q1.count())
        # 2. Pare out any for which there are no available builders
        q2=[]
        for bq in q1:
            dar = bq.build.distroarchrelease
            builders = notes[dar.processorfamily]["builders"]
            c = builders.countAvailable()
            if c > 0:
                q2.append(bq)
        self._logger.debug("After paring out non-available builders, %d NEEDSBUILD" % len(q2))
        # 3. Remove any for which there are no files (shouldn't happen but
        # worth checking for)
        q1 = q2
        q2 = []
        for bq in q1:
            if len(bq.build.sourcepackagerelease.files) > 0:
                #SourcePackageReleaseFile.selectBy(sourcepackagerelease = bq.build.sourcepackagerelease).count() > 0:
                q2.append(bq)
            else:
                self._logger.debug("Eliminating build of %s/%s/%s/%s/%s due to lack of source files" % (bq.build.distroarchrelease.distrorelease.distribution.name,
                                                                                                   bq.build.distroarchrelease.distrorelease.name,
                                                                                                   bq.build.distroarchrelease.architecturetag,
                                                                                                   bq.build.sourcepackagerelease.sourcepackagename.name,
                                                                                                   bq.build.sourcepackagerelease.version))
        self._logger.debug("After paring out any builds for which we lack source, %d NEEDSBUILD" % len(q2))
        # 4. Eliminate any which we know we can't build (e.g. for dependency
        # reasons)
        # XXX: dsilvers: 2005-02-22: Implement me?

        # And finally return that list
        return q2

    def scoreBuildQueueEntries(self, tobuild):
        for b in tobuild:
            # For now; each element gets a score of 1 point
            b.lastscore = 1

    def sortByScore(self, qitems):
        qitems.sort(lambda x, y: cmp(y.lastscore, x.lastscore))

    def sortAndSplitByProcessor(self, tobuild):
        # Split out each build by the processor it is to be built for
        # then order each sublist by its score
        ret = {}
        for bqi in tobuild:
            p = bqi.build.distroarchrelease.processorfamily
            l = ret.setdefault(p,[])
            l.append(bqi)

        for p in ret:
            self.sortByScore(ret[p])
            
        return ret

    def dispatchByProcessor(self, proc, qitems):
        self.getLogger().debug("dispatchByProcessor(%s, %d qitem%s)" % (
            proc.name, len(qitems), y(len(qitems)==1, '', 's')))
        builders = notes[proc]["builders"]
        b = builders.firstAvailable()
        while b is not None and len(qitems) > 0:
            self.startBuild(builders, b, qitems[0])
            qitems = qitems[1:]
            b = builders.firstAvailable()

    def startBuild(self, builders, builder, queueitem):
        self.getLogger().debug("startBuild(%s, %s %s)" % (
            builder.fqdn, queueitem.build.sourcepackagerelease.sourcepackagename.name, queueitem.build.sourcepackagerelease.version))
        # Find the list of files and give them to the builder...
        spr = queueitem.build.sourcepackagerelease
        files = spr.files
        filemap = {}
        for f in files:
            filemap[f.libraryfile.filename.encode("utf-8")] = f.libraryfile.content.sha1
            builders.givetobuilder(builder, f.libraryfile, self.downloader)
        builders.startBuild(builder, queueitem, filemap, "debian")
        self.commit()

    def scanActiveBuilders(self):
        # Find a list of all BuildQueue items which indicate they're active
        qitems = BuildQueue.select("BuildQueue.Builder IS NOT NULL")
        self.getLogger().debug("scanActiveBuilders() found %d active build(s) to check" % qitems.count())
        for aqi in qitems:
            proc = aqi.build.distroarchrelease.processorfamily
            builders = notes[proc]["builders"]
            builders.updateBuild(aqi, self.uploader)
            self.commit()
        
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

    distroreleases = Set()
    distroarchreleases = Set()
    
    # For every distroarchrelease we can find; put it into the build master
    for dar in DistroArchRelease.select():
        try:
            bm.addDistroArchRelease(dar)
            distroreleases.add(dar.distrorelease)
            distroarchreleases.add(dar)
        except Exception, e:
            logging.getLogger().warn("Unable to add %s/%s/%s to buildd" % (
                dar.distrorelease.distribution.name, dar.distrorelease.name,
                dar.architecturetag), exc_info=1)

    # For each distrorelease we care about; scan for sourcepackagereleases with
    # no build associated with the distroarchreleases we're interested in
    for dr in distroreleases:
        bm.checkForMissingBuilds(dr)

    # For each build record in NEEDSBUILD, ensure it has a buildqueue entry
    bm.addMissingBuildQueueEntries()

    # Scan all the pending builds; update logtails; retrieve builds where
    # they are compled
    bm.scanActiveBuilders()

    # Now that the dars are added, ask the buildmaster to calculate the set
    # of build candiates
    tobuild = bm.calculateCandidates()
    bm.scoreBuildQueueEntries(tobuild)
    byproc = bm.sortAndSplitByProcessor(tobuild)

    # Now that we've gathered in all the builds; dispatch the pending ones
    for proc in byproc:
        bm.dispatchByProcessor(proc, byproc[proc])
