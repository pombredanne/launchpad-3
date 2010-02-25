# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os
import pwd

from canonical.buildd.slave import BuildManager


class TranslationTemplatesBuildState(object):
    "States this kind of build goes through."""
    INIT = "INIT"
    UNPACK = "UNPACK"
    MOUNT = "MOUNT"
    UPDATE = "UPDATE"
    INSTALL = "INSTALL"
    GENERATE = "GENERATE"
    CLEANUP = "CLEANUP"


class TranslationTemplatesBuildManager(BuildManager):
    """Generate translation templates from branch.

    This is the implementation of `TranslationTemplatesBuildJob`.  The
    latter runs on the master server; TranslationTemplatesBuildManager
    runs on the build slave.
    """
    def __init__(self, *args, **kwargs):
        super(TranslationTemplatesBuildManager, self).__init__(
            *args, **kwargs)
        self._state = TranslationTemplatesBuildState.INIT
        self.alreadyfailed = False

    def initiate(self, files, chroot, extra_args):
        """See `BuildManager`."""
        self.branch_url = extra_args['branch_url']
        self.username = pwd.getpwuid(os.getuid())[0]

        super(TranslationTemplatesBuildManager, self).initiate(
            files, chroot, extra_args)

        self.chroot_path = os.path.join(
            self.home, 'build-' + self._buildid, 'chroot-autobuild')

    def iterate(self, success):
        func = getattr(self, 'iterate_' + self._state, None)
        if func is None:
            raise ValueError("Unknown %s state: %s" % (
                self.__class__.__name__, self._state))
        func(success)

    def iterate_INIT(self, success):
        """Next step after initialization."""
        if success == 0:
            self._state = TranslationTemplatesBuildState.UNPACK
            self.doUnpack()
        else:
            if not self.alreadyfailed:
                self._slave.builderFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.build_implementation.doCleanup()

    def iterate_UNPACK(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.MOUNT
            self.doMounting()
        else:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()

    def iterate_MOUNT(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.UPDATE
            self.doUpdate()
        else:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()

    def iterate_UPDATE(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.INSTALL
            self.doInstall()
        else:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()

    def iterate_INSTALL(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.GENERATE
            self.doGenerate()
        else:
            if not self.alreadyfailed:
                self._slave.chrootFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()

    def iterate_GENERATE(self, success):
        if success == 0:
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()
        else:
            if not self.alreadyfailed:
                self._slave.buildFail()
                self.alreadyfailed = True
            self._state = TranslationTemplatesBuildState.CLEANUP
            self.doCleanup()

    def iterate_CLEANUP(self, success):
        if success == 0:
            if not self.alreadyfailed:
                self._slave.buildOK()
        else:
            if not self.alreadyfailed:
                self._slave.builderFail()
                self.alreadyfailed = True
        self._slave.buildComplete()

    def doInstall(self):
        """Install packages required."""
        required_packages = [
            'bzr',
            'intltool-debian',
            ]
        command = ['apt-get', 'install', '-y'] + required_packages
        self.runInChroot(self.home, command, as_root=True)

    def doUpdate(self):
        """Update chroot."""
        command = ['update-debian-chroot', self._buildid]
        self.runInChroot(self.home, command, as_root=True)

    def doGenerate(self):
        """Generate templates."""
        command = ['generate-translation-templates.py', self.branch_url]
        self.runInChroot(self.home, command)

    def runInChroot(self, path, command, as_root=False):
        """Run command in chroot."""
        chroot = ['/usr/bin/sudo', '/usr/sbin/chroot', self.chroot_path]
        if as_root:
            sudo = []
        else:
            # We have to sudo to chroot, so if the command should _not_
            # be run as root, we then need to sudo back to who we were.
            sudo = ['/usr/bin/sudo', '-u', self.username]
        return self.runSubProcess(path, chroot + sudo + command)
