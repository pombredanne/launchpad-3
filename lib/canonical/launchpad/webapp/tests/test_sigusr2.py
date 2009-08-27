# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the SIGUSR2 signal handler."""

__metaclass__ = type
__all__ = []

import os.path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

class SIGUSR2TestCase(unittest.TestCase):
    def setUp(self):
        self.logdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.logdir)

    def test_sigusr2(self):
        main_log = os.path.join(self.logdir, 'main')
        cycled_log = os.path.join(self.logdir, 'cycled')

        helper_cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'sigusr2.py'),
            main_log]

        proc = subprocess.Popen(
            helper_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Wait until things have started up.
        while True:
            if os.path.exists(main_log):
                break
            self.assert_(
                proc.returncode is None,
                "Subprocess failed (%s): %s" % (proc.returncode, proc.stdout))

        # Make the helper emit a log message
        time.sleep(0.5)
        os.kill(proc.pid, signal.SIGUSR1)

        # The main logfile should no longer be empty
        content = self.getNewContent(main_log)
        self.failIfEqual(content, '')

        # Move the log file under the helper's feed
        os.rename(main_log, cycled_log)

        # Invoke the sigusr2 handler in the helper
        time.sleep(0.5)
        os.kill(proc.pid, signal.SIGUSR2)

        # Make the helper emit a log message
        time.sleep(0.5)
        os.kill(proc.pid, signal.SIGUSR1)

        # Wait for it to terminate.
        proc.wait()

        # Confirm content in the main log and the cycled log are what we
        # expect. We wait until the process has terminated to do this,
        # as before we might have made partial reads before the helper
        # had finished emitting its messages.
        self.assertEqual(open(cycled_log, 'r').read().strip(), 'Message 1')
        self.assertEqual(open(main_log, 'r').read().strip(), 'Message 2')


    def getNewContent(self, filename, previous_content=''):
        timeout = 10
        start_time = time.time()
        while time.time() < start_time + timeout:
            new_content = open(filename, 'r').read()
            if new_content != previous_content:
                return new_content
            time.sleep(0.05)
        self.fail("No new content in %s after 20 seconds." % filename)

