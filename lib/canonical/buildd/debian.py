# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Authors: Daniel Silverstone <daniel.silverstone@canonical.com>
#      and Adam Conrad <adam.conrad@canonical.com>

# Buildd Slave sbuild manager implementation

__metaclass__ = type

import os

from canonical.buildd.slave import (
    BuildManager,
    )


class DebianBuildState:
    """States for the DebianBuildManager."""
    INIT = "INIT"
    UNPACK = "UNPACK"
    MOUNT = "MOUNT"
    SOURCES = "SOURCES"
    UPDATE = "UPDATE"
    REAP = "REAP"
    UMOUNT = "UMOUNT"
    CLEANUP = "CLEANUP"


class DebianBuildManager(BuildManager):
    """Base behaviour for Debian chrooted builds."""

    def __init__(self, slave, buildid):
        BuildManager.__init__(self, slave, buildid)
        self._updatepath = slave._config.get("debianmanager", "updatepath")
        self._scanpath = slave._config.get("debianmanager", "processscanpath")
        self._sourcespath = slave._config.get("debianmanager", "sourcespath")
        self._cachepath = slave._config.get("slave","filecache")
        self._state = DebianBuildState.INIT
        slave.emptyLog()
        self.alreadyfailed = False

    @property
    def initial_build_state(self):
        raise NotImplementedError()

    def initiate(self, files, chroot, extra_args):
        """Initiate a build with a given set of files and chroot."""

        self.arch_tag = extra_args.get('arch_tag', self._slave.getArch())
        self.sources_list = extra_args.get('archives')

        BuildManager.initiate(self, files, chroot, extra_args)

    def doSourcesList(self):
        """Override apt/sources.list.

        Mainly used for PPA builds.
        """
        args = ["override-sources-list", self._buildid]
        args.extend(self.sources_list)
        self.runSubProcess(self._sourcespath, args)

    def doUpdateChroot(self):
        """Perform the chroot upgrade."""
        self.runSubProcess(
            self._updatepath,
            ["update-debian-chroot", self._buildid, self.arch_tag])

    def doRunBuild(self):
        """Run the main build process.

        Subclasses must override this.
        """
        raise NotImplementedError()

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

    def getChangesFilename(self):
        changes = self._dscfile[:-4] + "_" + self.arch_tag + ".changes"
        return get_build_path(self._buildid, changes)

    def gatherResults(self):
        """Gather the results of the build and add them to the file cache.

        The primary file we care about is the .changes file. We key from there.
        """
        path = self.getChangesFilename()
        name = os.path.basename(path)
        chfile = open(path, "r")
        self._slave.waitingfiles[name] = self._slave.storeFile(chfile.read())
        chfile.seek(0)
        seenfiles = False

        for fn in self._parseChangesFile(chfile):
            self._slave.addWaitingFile(get_build_path(self._buildid, fn))

        chfile.close()

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

    def iterate_INIT(self, success):
        """Just finished initializing the build."""
        if success != 0:
            if not self.alreadyfailed:
                # The init failed, can't fathom why that would be...
                self._slave.builderFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.CLEANUP
            self.doCleanup()
        else:
            self._state = DebianBuildState.UNPACK
            self.doUnpack()

    def iterate_UNPACK(self, success):
        """Just finished unpacking the tarball."""
        if success != 0:
            if not self.alreadyfailed:
                # The unpack failed for some reason...
                self._slave.chrootFail()
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
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = DebianBuildState.UMOUNT
            self.doUnmounting()
        else:
            if self.sources_list is not None:
                self._state = DebianBuildState.SOURCES
                self.doSourcesList()
            else:
                self._state = DebianBuildState.UPDATE
                self.doUpdateChroot()

    def getTmpLogContents(self):
        try:
            tmpLogHandle = open(os.path.join(self._cachepath, "buildlog"))
            return tmpLogHandle.read()
        finally:
            tmpLogHandle.close()

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
            self._state = self.initial_build_state
            self.doRunBuild()

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
                self._slave.buildOK()
        self._slave.buildComplete()


def get_build_path(build_id, *extra):
    """Generate a path within the build directory.

    :param build_id: the build id to use.
    :param extra: the extra path segments within the build directory.
    :return: the generated path.
    """
    return os.path.join(
        os.environ["HOME"], "build-" + build_id, *extra)
