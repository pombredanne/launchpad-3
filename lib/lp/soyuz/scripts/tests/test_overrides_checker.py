# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""archive-override-check tool base class tests."""

__metaclass__ = type

from unittest import TestCase

from lp.soyuz.scripts.ftpmaster import (
    PubBinaryContent,
    PubBinaryDetails,
    PubSourceChecker,
    )


class TestPubBinaryDetails(TestCase):

    def setUp(self):
        self.binary_details = PubBinaryDetails()

    def test_single_binary(self):
        """Single binary inclusion."""
        bin = PubBinaryContent('foo-dev', '1.0', 'i386', 'main',
                               'base', 'REQUIRED')

        self.binary_details.addBinaryDetails(bin)

        # components/sections/priorities have symetric behaviour

        # priorities[name] -> list of added priorities
        self.assertEqual(
            1, len(self.binary_details.priorities['foo-dev']))
        # not correct value was set yet
        self.assertEqual(
            False, 'foo-dev' in self.binary_details.correct_priorities)
        # set correct values
        self.binary_details.setCorrectValues()
        # now we have the correct value in place
        self.assertEqual(
            'REQUIRED', self.binary_details.correct_priorities['foo-dev'])

    def test_multi_binaries(self):
        """Multiple binaries inclusion."""
        values_map = [
            ('i386', 'REQUIRED'),
            ('amd64', 'REQUIRED'),
            ('powerpc', 'REQUIRED'),
            ('sparc', 'REQUIRED'),
            ('hppa', 'IMPORTANT'),
            ('ia64', 'IMPORTANT'),
            ]
        # add multiple binaries systematically according values_map
        for arch, priority in values_map:
            bin = PubBinaryContent('foo-dev', '1.0', arch, 'main',
                                   'base', priority)

            self.binary_details.addBinaryDetails(bin)

        # expects 2 distinct priorities
        self.assertEqual(
            2, len(self.binary_details.priorities['foo-dev']))
        # set correct values
        self.binary_details.setCorrectValues()
        # 'REQUIRED' is the most frequent priority in this group of binary
        self.assertEqual(
            'REQUIRED', self.binary_details.correct_priorities['foo-dev'])


class TestPubSourceChecker(TestCase):

    def setUp(self):
        """Initialize useful constant values."""
        self.name = 'foo'
        self.version = '1.0'
        self.component = 'main'
        self.section = 'python'
        self.urgency = 'URGENT'
        self.default_checker = PubSourceChecker(
            self.name, self.version, self.component,
            self.section, self.urgency)

    def test_initialization(self):
        """Check PubSourceChecker class initialization."""
        checker = self.default_checker
        self.assertEqual(self.name, checker.name)
        self.assertEqual(self.version, checker.version)
        self.assertEqual(self.component, checker.component)
        self.assertEqual(self.section, checker.section)
        self.assertEqual(self.urgency, checker.urgency)
        self.assertEqual(0, len(checker.binaries))

    def test_single_binary_ok(self):
        """Probe single correct binary addition."""
        checker = self.default_checker

        checker.addBinary('foo-dev', self.version, 'i386', self.component,
                          self.section, 'REQUIRED')

        checker.check()

        self.assertEqual(None, checker.renderReport())

        # inspect PubBinaryDetails attributesm check if they are populated
        # correctly see TestPubBinaryDetails above.
        self.assertEqual(
            1, len(checker.binaries_details.components['foo-dev']))
        self.assertEqual(
            1, len(checker.binaries_details.sections['foo-dev']))
        self.assertEqual(
            1, len(checker.binaries_details.priorities['foo-dev']))
        self.assertEqual(
            self.component,
            checker.binaries_details.correct_components['foo-dev'])
        self.assertEqual(
            self.section,
            checker.binaries_details.correct_sections['foo-dev'])
        self.assertEqual(
            'REQUIRED',
            checker.binaries_details.correct_priorities['foo-dev'])

    def test_multi_binary_component_failure(self):
        """Probe multi binary with wrong component."""
        checker = self.default_checker

        checker.addBinary('foo-dev', self.version, 'i386', 'universe',
                          self.section, 'REQUIRED')
        checker.addBinary('foo-dev', self.version, 'amd64', 'multiverse',
                          self.section, 'REQUIRED')

        checker.check()

        self.assertEqual(
            "foo_1.0 main/python/URGENT | 2 bin\n\t"
            "foo-dev_1.0 amd64 multiverse/python/REQUIRED\n\t\t"
            "W: Component mismatch: multiverse != universe",
            checker.renderReport())

    def test_multi_binary_priority_failure(self):
        """Probe multiple binaries with priority conflict."""
        checker = self.default_checker

        checker.addBinary('foo-dev', self.version, 'i386', self.component,
                          self.section, 'REQUIRED')
        checker.addBinary('foo-dbg', self.version, 'i386', self.component,
                          self.section, 'EXTRA')
        checker.addBinary('foo-dev', self.version, 'amd64', self.component,
                          self.section, 'EXTRA')

        checker.check()

        self.assertEqual(
            "foo_1.0 main/python/URGENT | 3 bin\n"
            "\tfoo-dev_1.0 amd64 main/python/EXTRA\n"
            "\t\tW: Priority mismatch: EXTRA != REQUIRED",
            checker.renderReport())

    def test_multi_binary_priority_success(self):
        """Probe multiple binaries with correct priorities.

        Following UNIX approach, no output is produce for correct input.
        """
        checker = self.default_checker

        checker.addBinary('foo-dev', self.version, 'i386', self.component,
                          self.section, 'EXTRA')
        checker.addBinary('foo-dbg', self.version, 'i386', self.component,
                          self.section, 'EXTRA')
        checker.addBinary('foo-dev', self.version, 'amd64', self.component,
                          self.section, 'EXTRA')

        checker.check()

        self.assertEqual(None, checker.renderReport())
