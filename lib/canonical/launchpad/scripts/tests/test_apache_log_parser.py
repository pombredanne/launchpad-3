# Copyright 2009 Canonical Ltd.  All rights reserved.

import os
import unittest

from canonical.launchpad.scripts.librarian_apache_log_parser import (
    get_date_status_and_request, get_method_and_file_id)


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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
