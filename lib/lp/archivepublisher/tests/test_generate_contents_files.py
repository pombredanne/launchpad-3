# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for the `generate-contents-files` script."""

__metaclass__ = type

from optparse import OptionValueError
import os.path
from textwrap import dedent

from canonical.config import config
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    ZopelessDatabaseLayer,
    )
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
    layer = ZopelessDatabaseLayer

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

    layer = LaunchpadZopelessLayer

    def makeContentArchive(self):
        """Prepare a "content archive" directory for script tests."""
        content_archive = self.makeTemporaryDirectory()
        config.push("content-archive", dedent("""\
            [archivepublisher]
            content_archive_root: %s
            """ % content_archive))
        self.addCleanup(config.pop, "content-archive")
        return content_archive

    def makeDistro(self):
        """Create a distribution for testing.

        The distribution will have a root directory set up, which will
        be cleaned up after the test.
        """
        return self.factory.makeDistribution(
            publish_root_dir=unicode(self.makeTemporaryDirectory()))

    def makeScript(self, distribution=None):
        """Create a script for testing."""
        if distribution is None:
            distribution = self.makeDistro()
        script = GenerateContentsFiles(test_args=['-d', distribution.name])
        script.logger = DevNullLogger()
        return script

    def test_name_is_consistent(self):
        distro = self.factory.makeDistribution()
        self.assertEqual(
            self.makeScript(distro).name, self.makeScript(distro).name)

    def test_name_is_unique_for_each_distro(self):
        self.assertNotEqual(self.makeScript().name, self.makeScript().name)

    def test_requires_distro(self):
        script = GenerateContentsFiles(test_args=[])
        self.assertRaises(OptionValueError, script.processOptions)

    def test_requires_real_distro(self):
        script = GenerateContentsFiles(
            test_args=['-d', self.factory.getUniqueString()])
        self.assertRaises(OptionValueError, script.processOptions)

    def test_looks_up_distro(self):
        distro = self.factory.makeDistribution()
        script = self.makeScript(distro)
        script.processOptions()
        self.assertEqual(distro, script.distribution)

    def test_queryDistro(self):
        distroseries = self.factory.makeDistroSeries()
        script = self.makeScript(distroseries.distribution)
        script.processOptions()
        self.assertEqual(distroseries.name, script.queryDistro('supported'))

    def test_getArchs(self):
        das = self.factory.makeDistroArchSeries()
        script = self.makeScript(das.distroseries.distribution)
        script.processOptions()
        self.assertEqual(das.architecturetag, script.getArchs())

    def test_writeAptContentsConf_writes_header(self):
        self.makeContentArchive()
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.writeAptContentsConf([], [])
        apt_contents_conf = file(
            "%s/%s-misc/apt-contents.conf"
            % (script.content_archive, distro.name)).read()
        self.assertIn('\nDefault\n{', apt_contents_conf)
        self.assertIn(distro.name, apt_contents_conf)

    def test_writeAptContentsConf_writes_suite_sections(self):
        content_archive = self.makeContentArchive()
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        suite = self.factory.getUniqueString('suite')
        arch = self.factory.getUniqueString('arch')
        script.writeAptContentsConf([suite], [arch])
        apt_contents_conf = file(
            "%s/%s-misc/apt-contents.conf"
            % (script.content_archive, distro.name)).read()
        self.assertIn('tree "dists/%s"\n' % suite, apt_contents_conf)
        overrides_path = os.path.join(
            content_archive, distro.name + "-contents",
            distro.name + "-overrides")
        self.assertIn('FileList "%s' % overrides_path, apt_contents_conf)
        self.assertIn('Architectures "%s source";' % arch, apt_contents_conf)

    def test_writeContentsTop(self):
        content_archive = self.makeContentArchive()
        distro = self.makeDistro()
        script = self.makeScript(distro)
        script.setUp()
        script.writeContentsTop()
        contents_top = file(
            "%s/%s-contents/%s-misc/Contents.top"
            % (content_archive, distro.name, distro.name)).read()
        self.assertIn("This file maps", contents_top)
        self.assertIn(distro.title, contents_top)
