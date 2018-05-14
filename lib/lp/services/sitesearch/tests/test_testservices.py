# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for sitesearch test service stubs."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type


import os
import unittest

from testscenarios import WithScenarios

from lp.services.osutils import process_exists
from lp.services.pidfile import pidfile_path
from lp.services.sitesearch import (
    bingtestservice,
    googletestservice,
    )


class TestServiceUtilities(WithScenarios, unittest.TestCase):
    """Test the service's supporting functions."""

    scenarios = [
        ("Bing", {
            "testservice": bingtestservice,
            }),
        ("Google", {
            "testservice": googletestservice,
            }),
        ]

    def test_stale_pid_file_cleanup(self):
        """The service should be able to clean up invalid PID files."""
        bogus_pid = 9999999
        self.assertFalse(
            process_exists(bogus_pid),
            "There is already a process with PID '%d'." % bogus_pid)

        # Create a stale/bogus PID file.
        filepath = pidfile_path(self.testservice.service_name)
        with file(filepath, 'w') as pidfile:
            pidfile.write(str(bogus_pid))

        # The PID clean-up code should silently remove the file and return.
        self.testservice.kill_running_process()
        self.assertFalse(
            os.path.exists(filepath),
            "The PID file '%s' should have been deleted." % filepath)