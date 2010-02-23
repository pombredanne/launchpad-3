# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad frontpage FunkLoad test"""

__metaclass__ = type
__all__ = []

import unittest

from funkload.FunkLoadTestCase import FunkLoadTestCase


class Frontpage(FunkLoadTestCase):
    """Test anonymous access to the Launchpad front page."""

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')

    def test_frontpage(self):
        self.get(self.server_url, description="Get /")

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")


if __name__ in ('main', '__main__'):
    unittest.main()
