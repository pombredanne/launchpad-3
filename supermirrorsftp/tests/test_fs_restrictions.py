
import os
import shutil

from twisted.trial import unittest

from supermirrorsftp.sftponly import SFTPOnlyAvatar
from supermirrorsftp.bazaarfs import SFTPServerRoot

class TestTopLevelDir(unittest.TestCase):
    def setUp(self):
        self.tmpdir = self.mktemp()
        os.mkdir(self.tmpdir)
        # A basic user dict, a member of no teams (aside from the user
        # themself).
        self.aliceUserDict = {
            'id': 1, 
            'name': 'alice', 
            'teams': [{'id': 1, 'name': 'alice'}],
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def testListDirNoTeams(self):
        # list only user dir + team dirs
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, '/dev/null',
                                self.aliceUserDict)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice'])

    def testListDirTeams(self):
        # list only user dir + team dirs
        
        # Add a team to Alice's user dict
        userDict = self.aliceUserDict.copy()
        userDict['teams'].append({'id': '2', 'name': 'test-team'})
        avatar = SFTPOnlyAvatar('alice', self.tmpdir, '/dev/null', userDict)
        root = SFTPServerRoot(avatar)
        self.assertEqual(
            [name for name, child in root.children()], 
            ['.', '..', '~alice', '~test-team'])

    def testAllWriteOpsForbidden(self):
        # mkdir
        # make new file
        # ...?
        pass

