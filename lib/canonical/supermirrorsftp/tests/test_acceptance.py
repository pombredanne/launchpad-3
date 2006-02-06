# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile
from cStringIO import StringIO
import os
import shutil

from bzrlib.branch import ScratchBranch
import bzrlib.branch
from bzrlib.tests import TestCase as BzrTestCase
from bzrlib.errors import NoSuchFile, NotBranchError
from bzrlib.transport import get_transport
from bzrlib.transport import sftp
from bzrlib.builtins import cmd_push

from twisted.python.util import sibpath

from canonical.launchpad import database
from canonical.launchpad.daemons.tachandler import TacTestSetup
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup
from canonical.database.sqlbase import sqlvalues


class AuthserverTacTestSetup(TacTestSetup):
    
    def __init__(self, root):
        self._root = root
    
    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)

    @property
    def root(self):
        return self._root

    @property
    def tacfile(self):
        # XXX: use standard LP authserver tac here instead, if possible
        return sibpath(__file__, 'authserver.tac')

    @property
    def pidfile(self):
        return os.path.join(self.root, 'authserver.pid')

    @property
    def logfile(self):
        return os.path.join(self.root, 'authserver.log')


class SFTPSetup(TacTestSetup):
    root = '/tmp/sftp-test'
    tacfile = '/home/andrew/warthogs/supermirrorsftp/devel/supermirrorsftp/tests/test.tac'
    pidfile = root + '/twistd.pid'
    logfile = root + '/twistd.log'
    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)


class AcceptanceTests(BzrTestCase):
    """ 
    These are the agreed acceptance tests for the Supermirror SFTP system's
    initial implementation of bzr support, converted from the English at
    https://wiki.launchpad.canonical.com/SupermirrorTaskList
    """

    def setUp(self):
        super(AcceptanceTests, self).setUp()

        # insert SSH keys for testuser -- and insert testuser!
        LaunchpadZopelessTestSetup().setUp()
        connection = LaunchpadZopelessTestSetup().connect()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE Person SET name = 'testuser' WHERE name = 'spiv';")
        cursor.execute(
            "UPDATE Person SET name = 'testteam' WHERE name = 'name17';")
        cursor.execute("""
            INSERT INTO SSHKey (person, keytype, keytext, comment)
            VALUES (7, 2,
            'AAAAB3NzaC1kc3MAAABBAL5VoWG5sy3CnLYeOw47L8m9A15hA/PzdX2u0B7c2Z1ktFPcEaEuKbLqKVSkXpYm7YwKj9y88A9Qm61CdvI0c50AAAAVAKGY0YON9dEFH3DzeVYHVEBGFGfVAAAAQCoe0RhBcefm4YiyQVwMAxwTlgySTk7FSk6GZ95EZ5Q8/OTdViTaalvGXaRIsBdaQamHEBB+Vek/VpnF1UGGm8YAAABAaCXDl0r1k93JhnMdF0ap4UJQ2/NnqCyoE8Xd5KdUWWwqwGdMzqB1NOeKN6ladIAXRggLc2E00UsnUXh3GE3Rgw==',
            'testuser');
            """)
        connection.commit()

        # XXX: start authserver.
        self.userHome = os.path.abspath(tempfile.mkdtemp())
        self.authserver = AuthserverTacTestSetup(self.userHome)
        self.authserver.setUp()

        #import logging
        #logging.basicConfig(level=logging.DEBUG)

        # Create a local branch with one revision
        self.local_branch = ScratchBranch(files=['foo'])
        self.local_branch.working_tree().add('foo')
        self.local_branch.working_tree().commit('Added foo')

        # Point $HOME at a test ssh config and key.
        import sys
        print >>sys.stderr, 'self.userHome:', self.userHome
        os.makedirs(os.path.join(self.userHome, '.ssh'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa'), 
            os.path.join(self.userHome, '.ssh', 'id_dsa'))
        shutil.copyfile(
            sibpath(__file__, 'id_dsa.pub'), 
            os.path.join(self.userHome, '.ssh', 'id_dsa.pub'))
        os.chmod(os.path.join(self.userHome, '.ssh', 'id_dsa'), 0600)
        self.realHome = os.environ['HOME']
        os.environ['HOME'] = self.userHome

        # XXX spiv 2005-01-13: 
        # Force bzrlib to use paramiko (because OpenSSH doesn't respect $HOME)
        self.realSshVendor = sftp._ssh_vendor
        sftp._ssh_vendor = 'none'

        # Start the SFTP server
        self.server = SFTPSetup()
        self.server.setUp()
        self.server_base = 'sftp://testuser@localhost:22222/'

    def tearDown(self):
        # Undo setUp.
        self.server.tearDown()
        os.environ['HOME'] = self.realHome
        self.authserver.tearDown()
        LaunchpadZopelessTestSetup().tearDown()
        super(AcceptanceTests, self).tearDown()
        sftp._ssh_vendor = self.realSshVendor

    def test_1_bzr_sftp(self):
        """
        The bzr client should be able to read and write to the Supermirror SFTP
        server just like another other SFTP server.  This means that actions
        like:
            * `bzr push sftp://testinstance/somepath`
            * `bzr log sftp://testinstance/somepath`
        (and/or their bzrlib equivalents) and so on should work, so long as the
        user has permission to read or write to those URLs.
        """
        
        remote_url = self.server_base + '~testuser/+junk/test-branch'
        self._push(remote_url)
        remote_branch = bzrlib.branch.Branch.open(remote_url)
        
        # Check that the pushed branch looks right
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

    def _push(self, remote_url):
        old_dir = os.getcwdu()
        os.chdir(self.local_branch.base)
        try:
            cmd_push().run_argv([remote_url])
        finally:
            os.chdir(old_dir)

    def test_2_namespace_restrictions(self):        
        """
        The namespace restrictions described in
        SupermirrorFilesystemHierarchy should be enforced. So operations
        such as:
            * `bzr push sftp://testinstance/~user/missing-product/new-branch`
            * `bzr push sftp://testinstance/~not-my-team/real-product/some-branch`
            * `bzr push sftp://testinstance/~team/+junk/anything`
        should fail.
        """

        # Cannot push branches to products that don't exist
        self._test_missing_parent_directory(
            '~testuser/product-that-does-not-exist/hello')

        # Teams do not have +junk products
        self._test_missing_parent_directory(
            '~testteam/+junk/hello')

        # Cannot push to team directories that the user isn't a member of --
        # they cannot see them at all.
        self._test_missing_parent_directory(
            '~not-my-team/real-product/hello')

        # XXX spiv 2006-01-11: what about lp-incompatible branch dir names (e.g.
        # capital Letters) -- Are they disallowed or accepted?  If accepted,
        # what will that branch's Branch.name be in the database?  Probably just
        # disallow, and try to have a tolerable error.

    def _test_missing_parent_directory(self, relpath):
        transport = get_transport(self.server_base + relpath).clone('..')
        self.assertRaises(
            NoSuchFile,
            transport.mkdir, 'hello')
        return transport

    def test_3_db_rename_branch(self):
        """
        Branches should be able to be renamed in the Launchpad webapp, and those
        renames should be immediately reflected in subsequent SFTP connections.

        Also, the renames may happen in the database for other reasons, e.g. if
        the DBA running a one-off script.
        """

        # Push the local branch to the server
        self._push(self.server_base + '~testuser/+junk/test-branch')

        # Rename branch in the database
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.selectOneBy(name='test-branch')
        branch_id = branch.id
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()
        remote_branch = bzrlib.branch.Branch.open(
            self.server_base + '~testuser/+junk/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())
        del remote_branch

        # Assign to a different product in the database.  This is effectively a
        # Rename as far as bzr is concerned: the URL changes.
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(branch_id)
        branch.product = database.Product.byName('firefox')
        LaunchpadZopelessTestSetup().txn.commit()
        self.assertRaises(
            NotBranchError,
            bzrlib.branch.Branch.open,
            self.server_base + '~testuser/+junk/renamed-branch')
        remote_branch = bzrlib.branch.Branch.open(
            self.server_base + '~testuser/firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())
        del remote_branch

        # Rename person in the database.  Again, the URL changes (and so does
        # the username we have to connect as!).
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(branch_id)
        branch.owner.name = 'renamed-user'
        LaunchpadZopelessTestSetup().txn.commit()
        server_base = self.server_base.replace('testuser', 'renamed-user')
        remote_branch = bzrlib.branch.Branch.open(
            server_base + '~renamed-user/firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())


    # Test 4: URL for mirroring
    #    There should be an API that can generate a URL for a branch for
    #    copy-to-mirror script to use. For example, for a branch with a database
    #    ID of 0xabcdef12, the URL may be something like
    #    `/srv/supermirrorsftp/branches/ab/cd/ef/12`.
    # This is covered by
    # canonical.launchpad.ftests.test_branchpulllist.test_branch_pull_render
    
    
    def test_5_mod_rewrite_data(self):
        """
        A mapping file for use with Apache's mod_rewrite should be generated
        correctly.
        """
        # We already test that the mapping file is correctly generated from the
        # database in
        # lib/canonical/launchpad/scripts/ftests/test_supermirror_rewritemap.py,
        # so here we just need to show that creating a branch puts the right
        # values in the database.

        # Push branch to sftp server
        self._push(self.server_base + '~testuser/+junk/test-branch')

        # Retrieve the branch from the database.  selectOne will fail if the
        # branch does not exist (or if somehow multiple branches match!).
        branch = database.Branch.selectOne(
            "owner = %s AND product IS NULL AND name = %s"
            % sqlvalues(database.Person.byName('testuser').id, 'test-branch'))

        self.assertEqual(None, branch.url)
        # If we get this far, the branch has been correctly inserted into the
        # database.




def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

