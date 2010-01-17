# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from unittest import TestLoader

from lp.testing import TestCaseWithFactory

from canonical.buildd.translationtemplates import (
    TranslationTemplatesBuildManager, TranslationTemplatesBuildState)


class FakeConfig:
    def get(self, section, key):
        return key


class FakeSlave:
    def __init__(self, tempdir):
        self._cachepath = tempdir
        self._config = FakeConfig()

    def cachePath(self, file):
        return os.path.join(self._cachepath, file)


class MockBuildManager(TranslationTemplatesBuildManager):
    def __init__(self, *args, **kwargs):
        super(MockBuildManager, self).__init__(*args, **kwargs)
        self.commands = []

    def runSubProcess(self, path, command):
        self.commands.append(command)
        return 0


class TestTranslationTemplatesBuildManagerIteration(TestCaseWithFactory):
    """Walk TranslationTemplatesBuildManager through its iteration steps."""
    def setUp(self):
        self.working_dir = self.makeTemporaryDirectory()
        slave_dir = os.path.join(self.working_dir, 'slave')
        home_dir = os.path.join(self.working_dir, 'home')
        for dir in (slave_dir, home_dir):
            os.mkdir(dir)
        slave = FakeSlave(slave_dir)
        buildid = '123'
        self.buildmanager = MockBuildManager(slave, buildid)
        self.buildmanager.home = home_dir
        self.chrootdir = os.path.join(
            home_dir, 'build-%s' % buildid, 'chroot-autobuild')

    def getState(self):
        """Retrieve build manager's state."""
        return self.buildmanager._state

    def test_initiate(self):
        # Creating a BuildManager spawns no child processes.
        self.assertEqual([], self.buildmanager.commands)

        # Initiating the build executes the first command.  It leaves
        # the build manager in the INIT state.
        self.buildmanager.initiate({}, 'chroot.tar.gz', {'branch_url': 'foo'})
        self.assertEqual(1, len(self.buildmanager.commands))
        self.assertEqual(TranslationTemplatesBuildState.INIT, self.getState())

    def test_iterate(self):
        url = 'lp:~my/branch'
        # The build manager's iterate() kicks off the consecutive states
        # after INIT.
        self.buildmanager.initiate({}, 'chroot.tar.gz', {'branch_url': url})

        # UNPACK: execute unpack-chroot.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.UNPACK, self.getState())
        self.assertEqual('unpack-chroot', self.buildmanager.commands[-1][0])

        # MOUNT: Set up realistic chroot environment.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.MOUNT, self.getState())
        self.assertEqual('mount-chroot', self.buildmanager.commands[-1][0])

        # UPDATE: Get the latest versions of installed packages.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.UPDATE, self.getState())
        expected_command = [
            '/usr/bin/sudo',
            '/usr/sbin/chroot', self.chrootdir,
            'update-debian-chroot',
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1][:4])

        # INSTALL: Install additional packages needed for this job into
        # the chroot.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.INSTALL, self.getState())
        expected_command = [
            '/usr/bin/sudo',
            '/usr/sbin/chroot', self.chrootdir,
            'apt-get',
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1][:4])

        # GENERATE: Run the slave's payload, the script that generates
        # templates.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.GENERATE, self.getState())
        expected_command = [
            '/usr/bin/sudo',
            '/usr/sbin/chroot', self.chrootdir,
            '/usr/bin/sudo', '-u', self.buildmanager.username,
            'generate-translation-templates.py',
            url,
            ]
        self.assertEqual(expected_command, self.buildmanager.commands[-1])

        # CLEANUP.
        self.buildmanager.iterate(0)
        self.assertEqual(
            TranslationTemplatesBuildState.CLEANUP, self.getState())
        self.assertEqual('remove-build', self.buildmanager.commands[-1][0])


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
