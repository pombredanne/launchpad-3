# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Functional tests for poppy FTP daemon."""

__metaclass__ = type

import ftplib
import os
import shutil
import socket
import tempfile
import unittest
import StringIO

from canonical.poppy.tests import PoppyTestSetup
from canonical.testing import LaunchpadZopelessLayer

class TestPoppy(unittest.TestCase):
    """Test if poppy.py daemon works properly."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        """Set up poppy in a temp dir."""
        self.root_dir = tempfile.mkdtemp()
        self.port = 3421
        self.poppy = PoppyTestSetup(self.root_dir, port=self.port,
                                    cmd='echo CLOSED')
        self.poppy.startPoppy()

    def tearDown(self):
        """Purge poppy root directory."""
        self.poppy.killPoppy()
        shutil.rmtree(self.root_dir)

    def getFTPConnection(self, login=True, user="ubuntu", password=""):
        """Build and return a FTP connection to the current poppy.

        Optionally log in with as 'annonymous' & empty password, or passed
        user/password.
        """
        conn = ftplib.FTP()
        # poppy usually takes sometime to come up, we need to wait, or insist.
        while True:
            try:
                reply = conn.connect("localhost", self.port)
            except socket.error:
                if not self.poppy.alive:
                    raise
            else:
                break

        if login:
            conn.login(user, password)
        return conn

    def waitForClose(self):
        """Wait for an FTP connection to close.

        Poppy is configured to echo 'CLOSED' to stdout when a
        connection closes, so we wait for CLOSED to appear in its
        output as a way to tell that the server has finished with the
        connection.
        """
        self.poppy.verify_output(['CLOSED'])

    def _uploadPath(self, path):
        """Return system path of specified path inside an upload.

        Only works for a single upload (poppy transaction).
        """
        contents = sorted(os.listdir(self.root_dir))
        upload_dir = contents[1]
        return os.path.join(self.root_dir, upload_dir, path)

    def testLOGIN(self):
        """Check login procedure."""
        conn = self.getFTPConnection(login=0)
        self.assertEqual(
            conn.login("annonymous", ""), "230 Login Successful.")
        conn.quit()

    def testCWD(self):
        """Check automatic creation of directories 'cwd'ed in.

        Also ensure they are created with proper permission (g+rwx)
        """
        conn = self.getFTPConnection()
        self.assertEqual(
            conn.cwd("foo/bar"), "250 CWD command successful.")
        self.assertEqual(
            conn.pwd(), "/foo/bar")
        conn.quit()
        self.waitForClose()
        wanted_path = self._uploadPath('foo/bar')

        self.assertTrue(os.path.exists(wanted_path))
        self.assertEqual(os.stat(wanted_path).st_mode, 040775)

    def testMKD(self):
        """Check recursive MKD (aka mkdir -p).

        Also ensure they are created with proper permission (g+rwx)
        """
        conn = self.getFTPConnection()
        self.assertEqual(
            conn.mkd("foo/bar"), "")
        self.assertEqual(
            conn.pwd(), "/")
        self.assertEqual(
            conn.cwd("foo/bar"), "250 CWD command successful.")
        self.assertEqual(
            conn.pwd(), "/foo/bar")
        conn.quit()
        self.waitForClose()
        wanted_path = self._uploadPath('foo/bar')

        self.assertTrue(os.path.exists(wanted_path))
        self.assertEqual(os.stat(wanted_path).st_mode, 040775)

    def testRMD(self):
        """Check recursive RMD (aka rmdir)"""
        conn = self.getFTPConnection()
        self.assertEqual(
            conn.mkd("foo/bar"), "")
        self.assertRaises(ftplib.error_perm, conn.rmd, "foo")
        self.assertEqual(
            conn.rmd("foo/bar"), "250 RMD command successful.")
        self.assertEqual(
            conn.rmd("foo"), "250 RMD command successful.")
        conn.quit()
        self.waitForClose()
        wanted_path = self._uploadPath('foo')
        self.assertFalse(os.path.exists(wanted_path))

    def testSTOR(self):
        """Check if the parent directories are created during file upload."""
        conn = self.getFTPConnection()
        fake_file = StringIO.StringIO("fake contents")
        self.assertEqual(
            conn.storbinary("STOR foo/bar/baz", fake_file),
            "226 Transfer successful.")
        conn.quit()
        self.waitForClose()
        wanted_path = self._uploadPath('foo/bar/baz')
        fs_content = open(os.path.join(wanted_path)).read()
        self.assertEqual(fs_content, "fake contents")

    def testUploadIsolation(self):
        """Check if poppy isolates the uploads properly.

        Upload should be done atomically, i.e., poppy should isolate the
        context according each connection/session.
        """
        # Perform a pair of sessions with distinct connections in time.
        conn_one = self.getFTPConnection()
        fake_file = StringIO.StringIO("ONE")
        self.assertEqual(
            conn_one.storbinary("STOR test", fake_file),
            "226 Transfer successful.")
        conn_one.quit()
        self.waitForClose()

        conn_two = self.getFTPConnection()
        fake_file = StringIO.StringIO("TWO")
        self.assertEqual(
            conn_two.storbinary("STOR test", fake_file),
            "226 Transfer successful.")
        conn_two.quit()
        self.waitForClose()

        # Perform a pair of sessions with simultaneous connections.
        conn_three = self.getFTPConnection()
        conn_four = self.getFTPConnection()

        fake_file = StringIO.StringIO("THREE")
        self.assertEqual(
            conn_three.storbinary("STOR test", fake_file),
            "226 Transfer successful.")

        fake_file = StringIO.StringIO("FOUR")
        self.assertEqual(
            conn_four.storbinary("STOR test", fake_file),
            "226 Transfer successful.")

        conn_three.quit()
        self.waitForClose()

        conn_four.quit()
        self.waitForClose()

        # Build a list of directories representing the 4 sessions.
        upload_dirs = [leaf for leaf in sorted(os.listdir(self.root_dir))
                       if not leaf.startswith(".") and
                       not leaf.endswith(".distro")]
        self.assertEqual(len(upload_dirs), 4)

        # Check the contents of files on each session.
        expected_contents = ['ONE', 'TWO', 'THREE', 'FOUR']
        for index in range(4):
            content = open(os.path.join(
                self.root_dir, upload_dirs[index], "test")).read()
            self.assertEqual(content, expected_contents[index])

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
