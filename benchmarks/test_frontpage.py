# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Launchpad frontpage FunkLoad test"""

__metaclass__ = type
__all__ = []

import unittest

from funkload.utils import Data
from funkload.FunkLoadTestCase import FunkLoadTestCase
from webunit.utility import Upload

from canonical.config import config

class Frontpage(FunkLoadTestCase):
    """Test anonymous access to the Launchpad front page."""

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.root_url = 'https://%s/' % config.vhost.mainsite.hostname

    def test_frontpage(self):
        self.get(self.root_url, description="Get frontpage")

    def tearDown(self):
        """Setting up test."""
        self.logd("tearDown.\n")


if __name__ in ('main', '__main__'):
    unittest.main()
