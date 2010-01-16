# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os

from unittest import TestLoader

from lp.testing import TestCaseWithFactory

from canonical.buildd.translationtemplates import (
    TranslationTemplatesBuildManager)


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

    def runSubProcess(self, command, args):
        self.commands.append((command, args))


class TestTranslationTemplatesBuildManager(TestCaseWithFactory):
    def setUp(self):
        self.working_dir = self.makeTemporaryDirectory()
        slave_dir = os.path.join(self.working_dir, 'slave')
        build_dir = os.path.join(self.working_dir, 'build')
        os.mkdir(slave_dir)
        os.mkdir(build_dir)
        slave = FakeSlave(slave_dir)
        self.buildmanager = MockBuildManager(
            slave, '123', base_path=build_dir)

    def test_init(self):
        self.assertContentEqual([], self.buildmanager.commands)

    def test_initiate(self):
        self.buildmanager.initiate({}, None, {'branch_url': 'foo'})
# XXX: This will fail, but let's just see what's in there.
        self.assertContentEqual([], self.buildmanager.commands)


def test_suite():
    return TestLoader().loadTestsFromName(__name__)
