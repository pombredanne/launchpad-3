# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

import gzip
import io

import responses

from lp.bugs.scripts.cveimport import CVEUpdater
from lp.services.log.logger import DevNullLogger
from lp.testing import TestCase


class TestCVEUpdater(TestCase):

    @responses.activate
    def test_fetch_uncompressed(self):
        # Fetching a URL returning uncompressed data works.
        url = 'http://cve.example.com/allitems.xml'
        body = b'<?xml version="1.0"?>'
        responses.add(
            'GET', url, headers={'Content-Type': 'text/xml'}, body=body)
        cve_updater = CVEUpdater(
            'cve-updater', test_args=[], logger=DevNullLogger())
        self.assertEqual(body, cve_updater.fetchCVEURL(url))

    @responses.activate
    def test_fetch_content_encoding_gzip(self):
        # Fetching a URL returning Content-Encoding: gzip works.
        url = 'http://cve.example.com/allitems.xml.gz'
        body = b'<?xml version="1.0"?>'
        gzipped_body_file = io.BytesIO()
        with gzip.GzipFile(fileobj=gzipped_body_file, mode='wb') as f:
            f.write(body)
        responses.add(
            'GET', url,
            headers={
                'Content-Type': 'text/xml',
                'Content-Encoding': 'gzip',
            },
            body=gzipped_body_file.getvalue())
        cve_updater = CVEUpdater(
            'cve-updater', test_args=[], logger=DevNullLogger())
        self.assertEqual(body, cve_updater.fetchCVEURL(url))

    @responses.activate
    def test_fetch_gzipped(self):
        # Fetching a URL returning gzipped data without Content-Encoding works.
        url = 'http://cve.example.com/allitems.xml.gz'
        body = b'<?xml version="1.0"?>'
        gzipped_body_file = io.BytesIO()
        with gzip.GzipFile(fileobj=gzipped_body_file, mode='wb') as f:
            f.write(body)
        responses.add(
            'GET', url, headers={'Content-Type': 'application/x-gzip'},
            body=gzipped_body_file.getvalue())
        cve_updater = CVEUpdater(
            'cve-updater', test_args=[], logger=DevNullLogger())
        self.assertEqual(body, cve_updater.fetchCVEURL(url))
