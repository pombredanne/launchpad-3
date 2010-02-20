# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from lp.soyuz.scripts.ppa_apache_log_parser import get_ppa_file_key
from lp.testing import TestCase


class TestPathParsing(TestCase):
    """Test parsing of PPA request paths."""

    def test_get_ppa_file_key_parses_good_paths(self):
        # A valid binary path results in archive, archive owner,
        # distribution and file names.
        archive_owner, archive_name, distro_name, filename = get_ppa_file_key(
            '/cprov/ppa/ubuntu/pool/main/f/foo/foo_1.2.3-4_i386.deb')

        self.assertEqual(archive_owner, 'cprov')
        self.assertEqual(archive_name, 'ppa')
        self.assertEqual(distro_name, 'ubuntu')
        self.assertEqual(filename, 'foo_1.2.3-4_i386.deb')

    def test_get_ppa_file_key_ignores_bad_paths(self):
        # A path with extra path segments returns None, to indicate that
        # it should be ignored.
        self.assertIs(None, get_ppa_file_key(
            '/cprov/ppa/ubuntu/pool/main/aha/f/foo/foo_1.2.3-4_i386.deb'))
        self.assertIs(None, get_ppa_file_key('/foo'))

    def test_get_ppa_file_key_ignores_non_binary_path(self):
        # A path with extra path segments returns None, to indicate that
        # it should be ignored.
        self.assertIs(None, get_ppa_file_key(
            '/cprov/ppa/ubuntu/pool/main/f/foo/foo_1.2.3-4.dsc'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
