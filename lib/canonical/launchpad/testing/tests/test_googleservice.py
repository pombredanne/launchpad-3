# Copyright 2008 Canonical Ltd.  All rights reserved.

"""
Unit tests for the Google test service stub.
"""

__metaclass__ = type


from canonical.launchpad.testing import googletestservice
from canonical.lazr.pidfile import pidfile_path
import errno
import os
import unittest


class TestServiceUtilities(unittest.TestCase):
    """Test the service's supporting functions."""

    def test_stale_pid_file_cleanup(self):
        """The service should be able to clean up invalid PID files."""
        bogus_pid = 9999999
        self.failIf(process_exists(bogus_pid),
                    "There is already a process with PID '%d'." % bogus_pid)

        # Create a stale/bogus PID file.
        filepath = pidfile_path(googletestservice.service_name)
        pidfile = file(filepath, 'w')
        pidfile.write(str(bogus_pid))
        pidfile.close()

        # The PID clean-up code should silently remove the file and return.
        googletestservice.kill_running_process()
        self.failIf(os.path.exists(filepath),
                    "The PID file '%s' should have been deleted." % filepath)


def process_exists(pid):
    """Return True if the specified process already exists."""
    try:
        os.kill(pid, 0)
    except os.error, err:
        if err.errno == errno.ESRCH:
            # All is well - the process doesn't exist.
            return False
        else:
            # We got a strange OSError, which we'll pass upwards.
            raise
    return True


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
