
import os
import shutil

from twisted.trial import unittest

from supermirrorsftp.sftponly import SFTPOnlyAvatar
from supermirrorsftp.bazaarfs import SFTPServerRoot

class TestTopLevelDir(unittest.TestCase):
    def testListDir(self):
        # list only user dir + team dirs
        tmpdir = self.mktemp()
        os.mkdir(tmpdir)
        userDict = {'id': 1, 'name': 'alice', 'teams': []}
        avatar = SFTPOnlyAvatar('alice', tmpdir, '/dev/null', userDict)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice'])
        shutil.rmtree(tmpdir)

    def testAllWriteOpsForbidden(self):
        # mkdir
        # make new file
        # ...?
        pass

