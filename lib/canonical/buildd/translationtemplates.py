# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
import pwd

from canonical.buildd.debian import DebianBuildManager, DebianBuildState

class TranslationTemplateBuildState(DebianBuildState):
    INSTALL = "INSTALL"
    GENERATE = "GENERATE"
    


class TranslationTemplatesBuildManager(DebianBuildManager):
    """Generate translation templates from branch.

    This is the implementation of `TranslationTemplatesBuildJob`.  The
    latter runs on the master server; TranslationTemplatesBuildManager
    runs on the build slave.
    """

    initial_build_state = TranslationTemplateBuildState.INSTALL

    def __init__(self, slave, buildid):
        super(TranslationTemplatesBuildManager, self).__init__(slave, buildid)
        self._generatepath = slave._config.get(
            "translationtemplatesmanager", "generatepath")

    def initiate(self, files, chroot, extra_args):
        """See `BuildManager`."""
        self.branch_url = extra_args['branch_url']
        self.username = pwd.getpwuid(os.getuid())[0]
        self.chroot_path = os.path.join(
            self.home, 'build-' + self._buildid, 'chroot-autobuild')

        super(TranslationTemplatesBuildManager, self).initiate(
            files, chroot, extra_args)

    def doInstall(self):
        """Install packages required."""
        required_packages = [
            'bzr',
            'intltool',
            'sudo',
            ]
        command = ['/usr/bin/apt-get', 'install', '-y'] + required_packages
        self.runInChroot(command, as_root=True)

    # To satisfy DebianPackageManagers needs without having a misleading
    # method name here.
    doRunBuild = doInstall

    def doGenerate(self):
        """Generate templates."""
        command = [self._generatepath, self.branch_url]
        self.runInChroot( command)

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
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()
        else:
            if not self.alreadyfailed:
                self._slave.buildFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.REAP
            self.doReapProcesses()

    def runInChroot(self, command, as_root=False):
        """Run command in chroot."""
        chroot = ['sudo', '/usr/sbin/chroot', self.chroot_path]
        if as_root:
            sudo = []
        else:
            # We have to sudo to chroot, so if the command should _not_
            # be run as root, we then need to sudo back to who we were.
            sudo = ['/usr/bin/sudo', '-u', self.username]
        return self.runSubProcess('/usr/bin/sudo', chroot + sudo + command)
