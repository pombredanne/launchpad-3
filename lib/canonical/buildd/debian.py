# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave sbuild manager implementation

from canonical.buildd.slave import BuildManager
from canonical.buildd.slave import RunCapture
import os
from os import environ

class DebianBuildManager(BuildManager):
    """Handle buildd building for a debian style build, using sbuild"""

    def __init__(self, slave, buildid):
        BuildManager.__init__(self,slave,buildid)
        self._sbuildpath = slave._config.get("debianmanager", "sbuildpath")
        self._updatepath = slave._config.get("debianmanager", "updatepath")
        self._scanpath = slave._config.get("debianmanager", "processscanpath")
        self._sbuildargs = slave._config.get("debianmanager", "sbuildargs").split(" ")
        self._state = 0
        slave.emptyLog()
        self.alreadyfailed = False

    def initiate(self, files, chroot):
        self._dscfile = None
        for f in files:
            if f.endswith(".dsc"):
                self._dscfile = f
        if self._dscfile is None:
            raise ValueError, files
        BuildManager.initiate(self, files, chroot)

    def doUpdateChroot(self):
        self.runSubProcess( self._updatepath,
                            ["update-debian-chroot", self._buildid] )

    def doRunSbuild(self):
        args = ["sbuild-package", self._buildid ]
        args.extend(self._sbuildargs)
        args.extend([self._dscfile])
        self.runSubProcess( self._sbuildpath, args )

    def doReapProcesses(self):
        self.runSubProcess( self._scanpath, [self._scanpath, self._buildid] )

    def gatherResults(self):
        # Gather the result files, and add them to the file cache
        # The only file we *know* will exist is the changes file
        changes = self._dscfile[:-4] + "_" + self._slave.arch() + ".changes"
        chfile = open(environ["HOME"]+"/build-"+self._buildid+"/"+changes, "r")
        filemap = {}
        filemap[changes] = self._slave.give(chfile.read())
        chfile.seek(0)
        seenfiles = False
        for l in chfile:
            if l.endswith("\n"):
                l = l[:-1]
            print "Line: %s" % l
            if not seenfiles and l.startswith("Files:"):
                print "Found the Files: line"
                seenfiles = True
            elif seenfiles:
                fn = l.split(" ")[-1]
                print "Adding %s to the list" % fn
                f = open(environ["HOME"]+"/build-"+self._buildid+"/"+fn, "r")
                filemap[fn] = self._slave.give(f.read())
                f.close()
        chfile.close()
        self._slave.waitingfiles(filemap)

    def iterate(self, success):
        print "Iterating with success flag %d against stage %d" % (success,self._state)
        if self._state == 0:
            # Just finished unpacking the tarball
            if success != 0:
                # The unpack failed for some reason...
                self._slave.builderFail()
                self._state = 11
                self.alreadyfailed = True
                self.doCleanup()
                return
            else:
                self._state = 1
                self.doMounting()
        elif self._state == 1:
            # Just finished doing the mounts
            if success != 0:
                self._slave.builderFail()
                self._state = 10
                self.alreadyfailed = True
                self.doUnmounting()
                return
            else:
                self._state = 2
                self.doUpdateChroot()
        elif self._state == 2:
            # Just finished updateing the chroot
            if success != 0:
                self._slave.chrootFail()
                self._state = 10
                self.alreadyfailed = True
                self.doUnmounting()
                return
            self._state = 3
            self.doRunSbuild()
        elif self._state == 3:
            # Finished the sbuild run
            if success != 0:
                if success == 1:
                    # deps failure
                    self._slave.depFail()
                elif success == 2:
                    # space issue -> builderfail
                    self._slave.builderFail()
                else:
                    # anything else is a buildfail
                    self._slave.buildFail()
                self._state = 10
                self.alreadyfailed = True
                self.doUnmounting()
                return
            self.gatherResults()
            self._state = 9
            self.doReapProcesses()
        elif self._state == 9:
            # Finished reaping processes; ignore error returns
            self._state = 10
            self.doUnmounting()
        elif self._state == 10:
            # Just finished doing the unmounting
            if success != 0:
                if not self.alreadyfailed:
                    self._slave.builderFail()
                    self.alreadyfailed = True
            self._state = 11
            self.doCleanup()
        elif self._state == 11:
            # Just finished the cleanup
            if success != 0:
                if not self.alreadyfailed:
                    self._slave.builderFail()
                    self.alreadyfailed = True
            else:
                # Successful clean
                if not self.alreadyfailed:
                    self._slave.buildComplete()
                else:
                    print "Build complete, but we had already failed :-("
        else:
            raise ValueError, self._state

