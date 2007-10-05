# Copyright Canonical Limited
# Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#      and Adam Conrad <adam.conrad@canonical.com>

# Buildd Slave sbuild manager implementation

__metaclass__ = type

import os
import re

from canonical.buildd.slave import (
    BuildManager, RunCapture
    )


class DebianBuildState:
    """States for the DebianBuildManager."""
    UNPACK = "UNPACK"
    MOUNT = "MOUNT"
    OGRE = "OGRE"
    SOURCES = "SOURCES"
    UPDATE = "UPDATE"
    SBUILD = "SBUILD"
    REAP = "REAP"
    UMOUNT = "UMOUNT"
    CLEANUP = "CLEANUP"


class SBuildExitCodes:
    """SBUILD process result codes."""
    OK = 0
    DEPFAIL = 1
    GIVENBACK = 2
    PACKAGEFAIL = 3
    BUILDERFAIL = 4


class BuildLogRegexes:
    """Build log regexes for performing actions based on regexes, and extracting dependencies for auto dep-waits"""
    GIVENBACK = [
        (" terminated by signal 4"),
        ("^E: There are problems and -y was used without --force-yes"),
        ("^make.* Illegal instruction"),
        ]
    DEPFAIL = [
        ("(?P<pk>[\-+.\w]+)\(inst [^ ]+ ! >> wanted (?P<v>[\-.+\w:~]+)\)","\g<pk> (>> \g<v>)"),
        ("(?P<pk>[\-+.\w]+)\(inst [^ ]+ ! >?= wanted (?P<v>[\-.+\w:~]+)\)","\g<pk> (>= \g<v>)"),
        ("(?s)^E: Couldn't find package (?P<pk>[\-+.\w]+)(?!.*^E: Couldn't find package)","\g<pk>"),
        ("(?s)^E: Package (?P<pk>[\-+.\w]+) has no installation candidate(?!.*^E: Package)","\g<pk>"),
        ]


class DebianBuildManager(BuildManager):
    """Handle buildd building for a debian style build, using sbuild"""

    def __init__(self, slave, buildid):
        BuildManager.__init__(self,slave,buildid)
        self._sbuildpath = slave._config.get("debianmanager", "sbuildpath")
        self._updatepath = slave._config.get("debianmanager", "updatepath")
        self._scanpath = slave._config.get("debianmanager", "processscanpath")
        self._sbuildargs = slave._config.get("debianmanager",
                                             "sbuildargs").split(" ")
        self._ogrepath = slave._config.get("debianmanager", "ogrepath")
        self._sourcespath = slave._config.get("debianmanager", "sourcespath")
        self._cachepath = slave._config.get("slave","filecache")
        self._state = DebianBuildState.UNPACK
        slave.emptyLog()
        self.alreadyfailed = False

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot."""
        self._dscfile = None
        for f in files:
            if f.endswith(".dsc"):
                self._dscfile = f
        if self._dscfile is None:
            raise ValueError, files
        if 'ogrecomponent' in extra_args:
            # Ubuntu refers to the concept that "main sees only main
            # while building" etc as "The Ogre Model" (onions, layers
            # and all). If we're given an ogre component, use it
            self.ogre = extra_args['ogrecomponent']
        else:
            self.ogre = False
        if 'archives' in extra_args and extra_args['archives']:
            self.sources_list = extra_args['archives']
        else:
            self.sources_list = None
        if 'arch_indep' in extra_args:
            self.arch_indep = extra_args['arch_indep']
        else:
            self.arch_indep = False

        BuildManager.initiate(self, files, chroot, extra_args)

    def doOgreModel(self):
        """Perform the ogre model activation."""
        self.runSubProcess(self._ogrepath,
                           ["apply-ogre-model", self._buildid, self.ogre])

    def doSourcesList(self):
        """Override apt/sources.list.

        Mainly used for PPA builds.
        """
        # XXX cprov 2007-05-17: It 'undo' ogre-component changes.
        # for PPAs it must be re-implemented on builddmaster side.
        args = ["override-sources-list", self._buildid]
        args.extend(self.sources_list)
        self.runSubProcess(self._sourcespath, args)

    def doUpdateChroot(self):
        """Perform the chroot upgrade."""
        self.runSubProcess(self._updatepath,
                           ["update-debian-chroot", self._buildid])

    def doRunSbuild(self):
        """Run the sbuild process to build the package."""
        args = ["sbuild-package", self._buildid ]
        args.extend(self._sbuildargs)
        if self.arch_indep:
            args.extend(["-A"])
        args.extend(["--comp=" + self.ogre])
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
        # XXX: dsilvers 2005-03-17: This join thing needs to be split out
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
            # Run OGRE if we need to, else run UPDATE
            if self.ogre:
                self._state = DebianBuildState.OGRE
                self.doOgreModel()
            elif self.sources_list is not None:
                self._state = DebianBuildState.SOURCES
                self.doSourcesList()
            else:
                self._state = DebianBuildState.UPDATE
                self.doUpdateChroot()

    def iterate_OGRE(self, success):
        """Just finished running the ogre applicator."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
        else:
            if self.sources_list is not None:
                self._state = DebianBuildState.SOURCES
                self.doSourcesList()
            else:
                self._state = DebianBuildState.UPDATE
                self.doUpdateChroot()

    def iterate_SOURCES(self, success):
        """Just finished overwriting sources.list."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
        else:
            self._state = DebianBuildState.UPDATE
            self.doUpdateChroot()

    def iterate_UPDATE(self, success):
        """Just finished updating the chroot."""
        if success != 0:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
        else:
            self._state = DebianBuildState.SBUILD
            self.doRunSbuild()

    def iterate_SBUILD(self, success):
        """Finished the sbuild run."""
        if success != SBuildExitCodes.OK:
            tmpLogHandle = open(os.path.join(self._cachepath, "buildlog"))
            tmpLog = tmpLogHandle.read()
            tmpLogHandle.close()
            if (success == SBuildExitCodes.DEPFAIL or
                success == SBuildExitCodes.PACKAGEFAIL):
                for rx in BuildLogRegexes.GIVENBACK:
                    mo=re.search(rx, tmpLog, re.M)
                    if mo:
                        success = SBuildExitCodes.GIVENBACK

            if success == SBuildExitCodes.DEPFAIL:
                for rx, dep in BuildLogRegexes.DEPFAIL:
                    mo=re.search(rx, tmpLog, re.M)
                    if mo:
                        if not self.alreadyfailed:
                            print("Returning build status: DEPFAIL")
                            print("Dependencies: " + mo.expand(dep))
                            self._slave.depFail(mo.expand(dep))
                            success = SBuildExitCodes.DEPFAIL
                            break
                    else:
                        success = SBuildExitCodes.PACKAGEFAIL

            if success == SBuildExitCodes.GIVENBACK:
                if not self.alreadyfailed:
                    print("Returning build status: GIVENBACK")
                    self._slave.giveBack()
            elif success == SBuildExitCodes.PACKAGEFAIL:
                if not self.alreadyfailed:
                    print("Returning build status: PACKAGEFAIL")
                    self._slave.buildFail()
            elif success >= SBuildExitCodes.BUILDERFAIL:
                # anything else is assumed to be a buildd failure
                if not self.alreadyfailed:
                    print("Returning build status: BUILDERFAIL")
                    self._slave.builderFail()
            self.alreadyfailed = True
            self._state = DebianBuildState.REAP
            self.doReapProcesses()
        else:
            print("Returning build status: OK")
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
