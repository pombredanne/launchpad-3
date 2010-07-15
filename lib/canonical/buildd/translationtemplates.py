# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from canonical.buildd.debian import DebianBuildManager, DebianBuildState


class TranslationTemplatesBuildState(DebianBuildState):
    INSTALL = "INSTALL"
    GENERATE = "GENERATE"


class TranslationTemplatesBuildManager(DebianBuildManager):
    """Generate translation templates from branch.

    This is the implementation of `TranslationTemplatesBuildJob`.  The
    latter runs on the master server; TranslationTemplatesBuildManager
    runs on the build slave.
    """

    initial_build_state = TranslationTemplatesBuildState.INSTALL

    def __init__(self, slave, buildid):
        super(TranslationTemplatesBuildManager, self).__init__(slave, buildid)
        self._generatepath = slave._config.get(
            "translationtemplatesmanager", "generatepath")
        self._resultname = slave._config.get(
            "translationtemplatesmanager", "resultarchive")

    def initiate(self, files, chroot, extra_args):
        """See `BuildManager`."""
        self._branch_url = extra_args['branch_url']
        self._chroot_path = os.path.join(
            self.home, 'build-' + self._buildid, 'chroot-autobuild')

        super(TranslationTemplatesBuildManager, self).initiate(
            files, chroot, extra_args)

    def doInstall(self):
        """Install packages required."""
        required_packages = [
            'bzr',
            'intltool',
            ]
        command = ['apt-get', 'install', '-y'] + required_packages
        chroot = ['sudo', 'chroot', self._chroot_path]
        self.runSubProcess('/usr/bin/sudo', chroot + command)

    # To satisfy DebianPackageManagers needs without having a misleading
    # method name here.
    doRunBuild = doInstall

    def doGenerate(self):
        """Generate templates."""
        command = [
            self._generatepath,
            self._buildid, self._branch_url, self._resultname]
        self.runSubProcess(self._generatepath, command)

    def gatherResults(self):
        """Gather the results of the build and add them to the file cache."""
        # The file is inside the chroot, in the home directory of the buildd
        # user. Should be safe to assume the home dirs are named identically.
        assert self.home.startswith('/'), "home directory must be absolute."

        path = os.path.join(
            self._chroot_path, self.home[1:], self._resultname)
        if os.access(path, os.F_OK):
            self._slave.addWaitingFile(path)

    def iterate_INSTALL(self, success):
        """Installation was done."""
        if success == 0:
            self._state = TranslationTemplatesBuildState.GENERATE
            self.doGenerate()
        else:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.UMOUNT
            self.doUnmounting()

    def iterate_GENERATE(self, success):
        """Template generation finished."""
        if success == 0:
            # It worked! Now let's bring in the harvest.
            self.gatherResults()
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()
        else:
            if not self.alreadyfailed:
                self._slave.buildFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()

