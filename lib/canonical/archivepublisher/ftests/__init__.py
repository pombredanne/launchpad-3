# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import sys
import subprocess
import signal
import fcntl
import time

from canonical.config import config

class SoyuzUploadError(Exception):
    """Used in the soyuz-upload test."""

class PoppyTestSetup:
    """Provides a setup and teardown mechanism for a poppy subprocess instance.

    Use this like you would LibrarianTestSetup or similar.
    """

    def __init__(self, fsroot,
                 user='ubuntutest',
                 cmd='echo @distro@; ls @fsroot@',
                 port=3421):
        self.fsroot = fsroot
        self.user = user
        self.cmd = cmd
        self.port = str(port)
        self.running = False

    def startPoppy(self):
        """Start the poppy instance."""
        script = os.path.join(config.root, "daemons/poppy-upload.py")
        self.process = subprocess.Popen([sys.executable, script,
                                         "--allow-user", self.user,
                                         "--cmd", self.cmd,
                                         self.fsroot, self.port],
                                        stdout=subprocess.PIPE)
        self.running = True

    def setNonBlocking(self):
        """Ensure that Poppy's stdout is nonblocking."""
        flags = fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_GETFL, 0)
        flags |= os.O_NONBLOCK
        fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_SETFL, flags)

    def killPoppy(self):
        """Kill the poppy instance dead."""
        if not self.alive:
            return
        os.kill(self.process.pid, signal.SIGTERM)
        # Give poppy a chance to die
        time.sleep(2)
        # Look to see if it has died yet
        ret = self.process.poll()
        if ret is None:
            # Poppy had not died, so send it SIGKILL
            os.kill(self.process.pid, signal.SIGKILL)
        # Finally return the result.
        self.running = False
        return self.process.wait()

    @property
    def alive(self):
        """Whether or not the poppy instance is still alive."""
        if not self.running:
            return False
        return self.process.poll() is None


    def read(self):
        """Read some bytes from Poppy's stdout."""
        return self.process.stdout.read()


    def verify_output(self, expected):
        """Verify that poppy writes the expected output."""
        now = time.time()
        timeout = 60
        buffer = ""
        while time.time() - now < timeout:
            if not self.alive:
                raise SoyuzUploadError("Poppy died unexpectedly")
            data = self.read()
            if data:
                now = time.time() # Reset the timout
                buffer += data
                lines = buffer.splitlines()
                for line in lines:
                    if line == self.user:
                        continue
                    if line not in expected:
                        raise SoyuzUploadError("Unexpected line found in "
                                               "poppy output: %r" % line)
                    expected.remove(line)
                buffer = ""
            if not expected:
                break
            time.sleep(0.5)
        else:
            raise SoyuzUploadError("FTP server timed out. The following "
                                   "was expected but not yet received: %r"
                                   % expected)
