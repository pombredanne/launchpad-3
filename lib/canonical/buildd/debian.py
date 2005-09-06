# Copyright Canonical Limited
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>

# Buildd Slave sbuild manager implementation

__metaclass__ = type

import os

from canonical.buildd.slave import (
    BuildManager, RunCapture
    )


class DebianBuildState:
    """States for the DebianBuildManager."""
    
    UNPACK = "UNPACK"
    MOUNT = "MOUNT"
    UPDATE = "UPDATE"
    SBUILD = "SBUILD"
    REAP = "REAP"
    UMOUNT = "UMOUNT"
    CLEANUP = "CLEANUP"


class SBuildExitCodes:
    """SBUILD process result codes."""
    OK = 0
    DEPFAIL = 1
    BUILDERFAIL = 2


class DebianBuildManager(BuildManager):
    """Handle buildd building for a debian style build, using sbuild"""

    def __init__(self, slave, buildid):
        BuildManager.__init__(self,slave,buildid)
        self._sbuildpath = slave._config.get("debianmanager", "sbuildpath")
        self._updatepath = slave._config.get("debianmanager", "updatepath")
        self._scanpath = slave._config.get("debianmanager", "processscanpath")
        self._sbuildargs = slave._config.get("debianmanager",
                                             "sbuildargs").split(" ")
        self._state = DebianBuildState.UNPACK
        slave.emptyLog()
        self.alreadyfailed = False

    def initiate(self, files, chroot):
        """Initiate a build with a given set of files and chroot."""
        self._dscfile = None
        for f in files:
            if f.endswith(".dsc"):
                self._dscfile = f
        if self._dscfile is None:
            raise ValueError, files
        BuildManager.initiate(self, files, chroot)

    def doUpdateChroot(self):
        """Perform the chroot upgrade."""
        self.runSubProcess( self._updatepath,
                            ["update-debian-chroot", self._buildid] )

    def doRunSbuild(self):
        """Run the sbuild process to build the package."""
        args = ["sbuild-package", self._buildid ]
        args.extend(self._sbuildargs)
        args.extend([self._dscfile])
        self.runSubProcess( self._sbuildpath, args )

    def doReapProcesses(self):
        """Reap any processes left lying around in the chroot."""
        self.runSubProcess( self._scanpath, [self._scanpath, self._buildid] )

    @staticmethod
    def _parseChangesFile(linesIter):
        """A generator that iterates over files listed in a changes file.
        
        :param linesIter: an iterable of lines in a changes file.
        """
        seenfiles = False
        for line in linesIter:
            if line.endswith("\n"):
                line = line[:-1]
            if not seenfiles and line.startswith("Files:"):
                seenfiles = True
            elif seenfiles:
                if not line.startswith(' '):
                    break
                filename = line.split(' ')[-1]
                yield filename

    def gatherResults(self):
        """Gather the results of the build and add them to the file cache.

        The primary file we care about is the .changes file. We key from there.
        """
        changes = self._dscfile[:-4] + "_" + self._slave.getArch() + ".changes"
        # XXX: dsilvers: 20050317: This join thing needs to be split out
        # into a method and unit tested.
        path = os.path.join(os.environ["HOME"], "build-"+self._buildid,
                            changes)
        chfile = open(path, "r")
        filemap = {}
        filemap[changes] = self._slave.storeFile(chfile.read())
        chfile.seek(0)
        seenfiles = False

        for fn in self._parseChangesFile(chfile):
            path = os.path.join(os.environ["HOME"], "build-"+self._buildid, fn)
            f = open(path, "r")
            filemap[fn] = self._slave.storeFile(f.read())
            f.close()

        chfile.close()
        self._slave.waitingfiles = filemap

    def iterate(self, success):
        # When a Twisted ProcessControl class is killed by SIGTERM, 
        # which we call 'build process aborted', 'None' is returned as
        # exit_code.
        print ("Iterating with success flag %s against stage %s"
               % (success, self._state))
        func = getattr(self, "iterate_" + self._state, None)
        if func is None:
            raise ValueError, "Unknown internal state " + self._state
        func(success)

    def iterate_UNPACK(self, success):
        """Just finished unpacking the tarball."""
        if success != 0:
            if not self.alreadyfailed:
                # The unpack failed for some reason...
                self._slave.builderFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.CLEANUP
            self.doCleanup()
        else:
            self._state = DebianBuildState.MOUNT
            self.doMounting()
            
    def iterate_MOUNT(self, success):
        """Just finished doing the mounts."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.builderFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.UMOUNT
            self.doUnmounting()
        else:
            self._state = DebianBuildState.UPDATE
            self.doUpdateChroot()

    def iterate_UPDATE(self, success):
        """Just finished updating the chroot."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.UMOUNT
            self.doUnmounting()
        else:
            self._state = DebianBuildState.SBUILD
            self.doRunSbuild()
            
    def iterate_SBUILD(self, success):
        """Finished the sbuild run."""
        if success != SBuildExitCodes.OK:
            if success == SBuildExitCodes.DEPFAIL:
                self._slave.depFail()
            elif success == SBuildExitCodes.BUILDERFAIL:
                self._slave.builderFail()
            else:
                # anything else is a buildfail
                if not self.alreadyfailed:
                    self._slave.buildFail()
                    self.alreadyfailed = True
            self._state = DebianBuildState.UMOUNT
            self.doUnmounting()
        else:
            self.gatherResults()
            self._state = DebianBuildState.REAP
            self.doReapProcesses()

    def iterate_REAP(self, success):
        """Finished reaping processes; ignore error returns."""
        self._state = DebianBuildState.UMOUNT
        self.doUnmounting()

    def iterate_UMOUNT(self, success):
        """Just finished doing the unmounting."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.builderFail()
                self.alreadyfailed = True
        self._state = DebianBuildState.CLEANUP
        self.doCleanup()

    def iterate_CLEANUP(self, success):
        """Just finished the cleanup."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.builderFail()
                self.alreadyfailed = True
        else:
            # Successful clean
            if not self.alreadyfailed:
                self._slave.buildComplete()
