# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from lp.testing import TestCase
from lp.testing.fakemethod import FakeMethod

from canonical.buildd.translationtemplates import (
    TranslationTemplatesBuildManager, TranslationTemplatesBuildState)


class FakeConfig:
    def get(self, section, key):
        return key


class FakeSlave:
    def __init__(self, tempdir):
        self._cachepath = tempdir
        self._config = FakeConfig()
        self._was_called = set()

    def cachePath(self, file):
        return os.path.join(self._cachepath, file)

    def anyMethod(self, *args, **kwargs):
        pass

    fake_methods = ['emptyLog', 'chrootFail', 'buildFail', 'builderFail',]
    def __getattr__(self, name):
        """Remember which fake methods were called."""
        if name not in self.fake_methods:
            raise AttributeError(
                "'%s' object has no attribute '%s'" % (self.__class__, name))
        self._was_called.add(name)
        return self.anyMethod

    def wasCalled(self, name):
        return name in self._was_called

    def getArch(self):
        return 'i386'

    addWaitingFile = FakeMethod()


class MockBuildManager(TranslationTemplatesBuildManager):
    def __init__(self, *args, **kwargs):
        super(MockBuildManager, self).__init__(*args, **kwargs)
        self.commands = []

    def runSubProcess(self, path, command):
        self.commands.append([path]+command)
        return 0


class TestTranslationTemplatesBuildManagerIteration(TestCase):
    """Run TranslationTemplatesBuildManager through its iteration steps."""
    def setUp(self):
        super(TestTranslationTemplatesBuildManagerIteration, self).setUp()
        self.working_dir = self.makeTemporaryDirectory()
        slave_dir = os.path.join(self.working_dir, 'slave')
        home_dir = os.path.join(self.working_dir, 'home')
        for dir in (slave_dir, home_dir):
            os.mkdir(dir)
        self.slave = FakeSlave(slave_dir)
        self.buildid = '123'
        self.buildmanager = MockBuildManager(self.slave, self.buildid)
        self.buildmanager.home = home_dir
        self.chrootdir = os.path.join(
            home_dir, 'build-%s' % self.buildid, 'chroot-autobuild')

    def getState(self):
        """Retrieve build manager's state."""
        return self.buildmanager._state

    def test_iterate(self):
        # Two iteration steps are specific to this build manager.
        url = 'lp:~my/branch'
        # The build manager's iterate() kicks off the consecutive states
        # after INIT.
        self.buildmanager.initiate({}, 'chroot.tar.gz', {'branch_url': url})

        # Skip states that are done in DebianBuldManager to the state
        # directly before INSTALL.
        self.buildmanager._state = TranslationTemplatesBuildState.UPDATE

        # INSTALL: Install additional packages needed for this job into
        # the chroot.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.INSTALL, self.getState())
        expected_command = [
            '/usr/bin/sudo',
            'sudo', 'chroot', self.chrootdir,
            'apt-get',
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1][:5])

        # GENERATE: Run the slave's payload, the script that generates
        # templates.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.GENERATE, self.getState())
        expected_command = [
            'generatepath', 'generatepath', self.buildid, url, 'resultarchive'
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1])
        self.assertFalse(self.slave.wasCalled('chrootFail'))

        outfile_path = os.path.join(
            self.chrootdir, self.buildmanager.home[1:],
            self.buildmanager._resultname)
        os.makedirs(os.path.dirname(outfile_path))

        outfile = open(outfile_path, 'w')
        outfile.write("I am a template tarball. Seriously.")
        outfile.close()

        # The control returns to the DebianBuildManager in the REAP state.
        self.buildmanager.iterate(0)
        expected_command = [
            'processscanpath', 'processscanpath', self.buildid
            ]
        self.assertEqual(
            TranslationTemplatesBuildState.REAP, self.getState())
        self.assertEqual(expected_command, self.buildmanager.commands[-1])
        self.assertFalse(self.slave.wasCalled('buildFail'))
        self.assertEqual(
            [((outfile_path,), {})], self.slave.addWaitingFile.calls)

    def test_iterate_fail_INSTALL(self):
        # See that a failing INSTALL is handled properly.
        url = 'lp:~my/branch'
        # The build manager's iterate() kicks off the consecutive states
        # after INIT.
        self.buildmanager.initiate({}, 'chroot.tar.gz', {'branch_url': url})

        # Skip states to the INSTALL state.
        self.buildmanager._state = TranslationTemplatesBuildState.INSTALL

        # The buildmanager fails and iterates to the UMOUNT state.
        self.buildmanager.iterate(-1)
        self.assertEqual(
            TranslationTemplatesBuildState.UMOUNT, self.getState())
        expected_command = [
            'umountpath', 'umount-chroot', self.buildid
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1])
        self.assertTrue(self.slave.wasCalled('chrootFail'))

    def test_iterate_fail_GENERATE(self):
        # See that a failing GENERATE is handled properly.
        url = 'lp:~my/branch'
        # The build manager's iterate() kicks off the consecutive states
        # after INIT.
        self.buildmanager.initiate({}, 'chroot.tar.gz', {'branch_url': url})

        # Skip states to the INSTALL state.
        self.buildmanager._state = TranslationTemplatesBuildState.GENERATE

        # The buildmanager fails and iterates to the REAP state.
        self.buildmanager.iterate(-1)
        expected_command = [
            'processscanpath', 'processscanpath', self.buildid
            ]
        self.assertEqual(
            TranslationTemplatesBuildState.REAP, self.getState())
        self.assertEqual(expected_command, self.buildmanager.commands[-1])
        self.assertTrue(self.slave.wasCalled('buildFail'))
