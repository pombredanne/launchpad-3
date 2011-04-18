# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the `generate-contents-files` script."""

__metaclass__ = type

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.archivepublisher.scripts.generate_contents_files import (
    differ_in_content,
    execute,
    GenerateContentsFiles,
    move_file,
    )
from lp.services.log.logger import DevNullLogger
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.services.utils import file_exists
from lp.testing import TestCaseWithFactory


def write_file(filename, content):
    """Write `content` to `filename`, and flush."""
    output_file = file(filename, 'w')
    output_file.write(content)
    output_file.close()


class TestHelpers(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_differ_in_content_returns_false_for_identical_files(self):
        self.useTempDir()
        text = self.factory.getUniqueString()
        write_file('one', text)
        write_file('other', text)
        self.assertFalse(differ_in_content('one', 'other'))

    def test_differ_in_content_returns_true_for_differing_files(self):
        self.useTempDir()
        write_file('one', self.factory.getUniqueString())
        write_file('other', self.factory.getUniqueString())
        self.assertTrue(differ_in_content('one', 'other'))

    def test_execute_raises_if_command_fails(self):
        logger = DevNullLogger()
        self.assertRaises(
            LaunchpadScriptFailure, execute, logger, "/bin/false")

    def test_execute_executes_command(self):
        self.useTempDir()
        logger = DevNullLogger()
        filename = self.factory.getUniqueString()
        execute(logger, "touch", [filename])
        self.assertTrue(file_exists(filename))

    def test_move_file_renames_file(self):
        self.useTempDir()
        text = self.factory.getUniqueString()
        write_file("old_name", text)
        move_file("old_name", "new_name")
        self.assertEqual(text, file("new_name").read())

    def test_move_file_overwrites_old_file(self):
        self.useTempDir()
        write_file("new_name", self.factory.getUniqueString())
        new_text = self.factory.getUniqueString()
        write_file("old_name", new_text)
        move_file("old_name", "new_name")
        self.assertEqual(new_text, file("new_name").read())


class TestGenerateContentsFiles(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def makeScript(self, distribution=None):
        if distribution is None:
            distribution = self.factory.makeDistribution()
        return GenerateContentsFiles(test_args=['-d', distribution.name])

    def test_name_is_consistent(self):
        distro = self.factory.makeDistribution()
        self.assertEqual(
            self.makeScript(distro).name, self.makeScript(distro).name)

    def test_name_is_unique_for_each_distro(self):
        self.assertNotEqual(self.makeScript().name, self.makeScript().name)
