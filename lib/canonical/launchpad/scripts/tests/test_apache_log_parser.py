# Copyright 2009 Canonical Ltd.  All rights reserved.

import os
import tempfile
import unittest

from canonical.launchpad.database.librarian import ParsedApacheLog
from canonical.launchpad.scripts.librarian_apache_log_parser import (
    get_date_status_and_request, get_files_to_parse, get_method_and_file_id)
from canonical.testing import LaunchpadZopelessLayer


here = os.path.dirname(__file__)


class TestLineParsing(unittest.TestCase):
    """Test parsing of lines of an apache log file."""

    def test_return_value(self):
        fd = open(
            os.path.join(here, 'apache-log-files', 'librarian-oneline.log'))
        date, status, request = get_date_status_and_request(fd.read())
        self.assertEqual(date, '[13/Jun/2008:18:38:57 +0100]')
        self.assertEqual(status, '200')
        self.assertEqual(
            request, 'GET /15166065/gnome-do-0.5.0.1.tar.gz HTTP/1.1')


class TestRequestParsing(unittest.TestCase):
    """Test parsing the request part of an apache log line."""

    def test_return_value(self):
        request = 'GET /8196569/mediumubuntulogo.png HTTP/1.1'
        method, file_id = get_method_and_file_id(request)
        self.assertEqual(method, 'GET')
        self.assertEqual(file_id, '8196569')


class TestParsedFilesDetection(unittest.TestCase):
    """Test the detection of already parsed logs."""

    layer = LaunchpadZopelessLayer
    # The directory in which the sample log files live.
    root = os.path.join(here, 'apache-log-files')

    def setUp(self):
        self.layer.switchDbUser('librarianlogparser')

    def test_not_parsed_file(self):
        # A file that has never been parsed will have to be parsed from the
        # start.
        file_name = 'launchpadlibrarian.net.access-log'
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [0])

    def test_completely_parsed_file(self):
        # A file that has been completely parsed will be skipped.
        file_name = 'launchpadlibrarian.net.access-log'
        content = open(os.path.join(self.root, file_name)).read()
        first_line, rest = content.split('\n', 1)
        parsed_file = ParsedApacheLog(first_line, len(content))

        self.failUnlessEqual(get_files_to_parse(self.root, [file_name]), {})

    def test_parsed_file_with_new_content(self):
        # A file that has been parsed already but in which new content was
        # added will be parsed again, starting from where parsing stopped last
        # time.
        file_name = 'launchpadlibrarian.net.access-log'
        content = open(os.path.join(self.root, file_name)).read()
        first_line, rest = content.split('\n', 1)
        parsed_file = ParsedApacheLog(first_line, len(first_line))

        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [len(first_line)])

    def test_different_files_with_same_name(self):
        # Thanks to log rotation, two runs of our script may see files with
        # the same name but completely different content.  If we see a file 
        # with a name matching that of an already parsed file but with content
        # differing from the last file with that name parsed, we know we need
        # to parse the file from the start.
        fd, file_name = tempfile.mkstemp()
        content1 = 'First Line\nSecond Line'
        first_line, rest = content1.split('\n', 1)
        parsed_file = ParsedApacheLog(first_line, len(content1))

        # This file has the same name of the previous one (which has been
        # parsed already), but its first line is different, so we'll have to
        # parse it from the start.
        content2 = 'Different First Line\nSecond Line'
        fd = open(file_name, 'w')
        fd.write(content2)
        fd.close()
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [0])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
