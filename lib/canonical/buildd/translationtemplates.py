# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from canonical.buildd.debian import DebianBuildManager, DebianBuildState

class TranslationTemplatesBuildState(DebianBuildState):
    INSTALL = "INSTALL"
    GENERATE = "GENERATE"
    UPLOAD = "UPLOAD"


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
        command = [self._generatepath, self._buildid, self._branch_url]
        self.runSubProcess(self._generatepath, command)

    def doUpload(self):
        """Upload generated templates to queue."""

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
        if success == 0:
            self._state = TranslationTemplatesBuildState.UPLOAD
            self.doUpload()
        else:
            if not self.alreadyfailed:
                self._slave.buildFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()

    def iterate_UPLOAD(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()
        else:
            if not self.alreadyfailed:
                self._slave.buildFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()

