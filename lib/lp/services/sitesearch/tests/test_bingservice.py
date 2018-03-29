# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Unit tests for the Bing test service stub.
"""

__metaclass__ = type


import os
import unittest

from lp.services.osutils import process_exists
from lp.services.pidfile import pidfile_path
from lp.services.sitesearch import bingtestservice


class TestServiceUtilities(unittest.TestCase):
    """Test the service's supporting functions."""

    def test_stale_pid_file_cleanup(self):
        """The service should be able to clean up invalid PID files."""
        bogus_pid = 9999999
        self.assertFalse(
            process_exists(bogus_pid),
            "There is already a process with PID '%d'." % bogus_pid)

        # Create a stale/bogus PID file.
        filepath = pidfile_path(bingtestservice.service_name)
        with file(filepath, 'w') as pidfile:
            pidfile.write(str(bogus_pid))

        # The PID clean-up code should silently remove the file and return.
        bingtestservice.kill_running_process()
        self.assertFalse(
            os.path.exists(filepath),
            "The PID file '%s' should have been deleted." % filepath)
