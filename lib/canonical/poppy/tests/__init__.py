# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import select
import signal
import subprocess
import sys
import time

from canonical.config import config

class SoyuzUploadError(Exception):
    """Used in the soyuz-upload test."""

class PoppyTestSetup:
    """Provides a setup and teardown mechanism for a poppy subprocess instance.

    Use this like you would LibrarianTestSetup or similar.
    """

    def __init__(self, fsroot,
                 user='anonymous',
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

    def verify_output(self, expected):
        """Verify that poppy writes the expected output."""
        timelimit = time.time() + 60
        buffer = ""
        while True:
            rlist, wlist, xlist = select.select(
                [self.process.stdout.fileno()], [], [], timelimit - time.time())
            if len(rlist) == 0:
                if self.process.poll() is not None:
                    raise SoyuzUploadError("Poppy died unexpectedly")
                # Try and kill poppy too?
                raise SoyuzUploadError(
                    "FTP server timed out. The following was expected:\n%r\n"
                    "But the following was received:\n%r\n"
                    % (expected, buffer))
            else:
                # reset the time limit
                timelimit = time.time() + 60
                chunk = os.read(self.process.stdout.fileno(), 4096)
                buffer += chunk
                # XXX: jamesh 2007-02-20:
                # We might have an incomplete line at the end of the
                # buffer.  This doesn't seem to be a problem for the
                # amount of data being written in the tests though.
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
                # stdout was closed before we read all the expected lines
                if chunk == "":
                    raise SoyuzUploadError("FTP server exited before the "
                                           "expected data was received: %r"
                                           % expected)
        else:
            raise SoyuzUploadError(
                "FTP server timed out.\n"
                "The following was expected:\n%r\n"
                "But the following was received:\n%r\n"
                % (expected, buffer))

