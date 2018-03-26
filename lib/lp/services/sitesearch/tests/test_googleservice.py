# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Unit tests for the Google test service stub.
"""

__metaclass__ = type


import os
import unittest

from lp.services.osutils import process_exists
from lp.services.pidfile import pidfile_path
from lp.services.sitesearch import googletestservice


class TestServiceUtilities(unittest.TestCase):
    """Test the service's supporting functions."""

    def test_stale_pid_file_cleanup(self):
        """The service should be able to clean up invalid PID files."""
        bogus_pid = 9999999
        self.assertFalse(
            process_exists(bogus_pid),
            "There is already a process with PID '%d'." % bogus_pid)

        # Create a stale/bogus PID file.
        filepath = pidfile_path(googletestservice.service_name)
        pidfile = file(filepath, 'w')
        pidfile.write(str(bogus_pid))
        pidfile.close()

        # The PID clean-up code should silently remove the file and return.
        googletestservice.kill_running_process()
        self.assertFalse(
            os.path.exists(filepath),
            "The PID file '%s' should have been deleted." % filepath)
