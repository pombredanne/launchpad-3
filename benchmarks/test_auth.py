# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Basic login to launchpad test."""

__metaclass__ = type
__all__ = []

import re
import threading
import unittest

from funkload.FunkLoadTestCase import FunkLoadTestCase


class Auth(FunkLoadTestCase):

    def setUp(self):
        """Setting up test."""
        self.logd("setUp")
        self.server_url = self.conf_get('main', 'url')

        _error_re = re.compile('(?s)class="error message">(.*?)</')

    def test_auth(self):
        """Runs the steps of a simple Launchpad login."""
        pass

    def tearDown(self):
        """Finishes the test."""
        pass


if __name__ in ('main', '__main__'):
    unittest.main()



