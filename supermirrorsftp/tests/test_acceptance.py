# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest
import tempfile
from cStringIO import StringIO

from bzrlib.branch import ScratchBranch
import bzrlib.branch
from bzrlib.workingtree import WorkingTree
from bzrlib.tests import TestCase as BzrTestCase
from bzrlib.errors import PermissionDenied, NoSuchFile, NotBranchError
from bzrlib.transport import get_transport
from bzrlib.transport import sftp

#from twisted.trial import unittest
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
        self.server = TestSFTPServer()

    def tearDown(self):
        # Undo setUp.
        self.server.stop()
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
        
        remote_url = self.server.base + '~testuser/+junk/test-branch'
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
        transport = get_transport(self.server.base + relpath).clone('..')
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
        self._push(self.server.base + '~testuser/+junk/test-branch')

        # Rename branch in the database
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.selectOneBy(name='test-branch')
        branch_id = branch.id
        branch.name = 'renamed-branch'
        LaunchpadZopelessTestSetup().txn.commit()
        remote_branch = bzrlib.branch.Branch.open(
            self.server.base + '~testuser/+junk/renamed-branch')
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
            self.server.base + '~testuser/+junk/renamed-branch')
        remote_branch = bzrlib.branch.Branch.open(
            self.server.base + '~testuser/firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())
        del remote_branch

        # Rename person in the database.  Again, the URL changes (and so does
        # the username we have to connect as!).
        LaunchpadZopelessTestSetup().txn.begin()
        branch = database.Branch.get(branch_id)
        branch.owner.name = 'renamed-user'
        LaunchpadZopelessTestSetup().txn.commit()
        self.server.base = self.server.base.replace('testuser', 'renamed-user')
        remote_branch = bzrlib.branch.Branch.open(
            self.server.base + '~renamed-user/firefox/renamed-branch')
        self.assertEqual(
            self.local_branch.last_revision(), remote_branch.last_revision())

    def test_4_url_for_mirror(self):
        """
        There should be an API that can generate a URL for a branch for
        copy-to-mirror script to use. For example, for a branch with a database
        ID of 0xabcdef12, the URL may be something like
        `/srv/supermirrorsftp/branches/ab/cd/ef/12`.
        """
        # Push branch to sftp server
        self._push(self.server.base + '~testuser/+junk/test-branch')
        branch_id = self.server.last_accessed_branch_id  # XXX

        # Generate the path for copy-to-mirror script to use
        mirror_from_path = get_path_for_copy_to_mirror(branch_id)

        # Construct a Branch object that reads directly from the on-disk storage
        # of the server.
        server_branch = bzrlib.branch.Branch.open(mirror_from_path)

        # Check that it's the branch we're looking for
        self.assertEqual(
            self.local_branch.last_revision(), server_branch.last_revision())
        
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
        self._push(self.server.base + '~testuser/+junk/test-branch')

        # Retrieve the branch from the database.  selectOne will fail if the
        # branch does not exist (or if somehow multiple branches match!).
        branch = database.Branch.selectOne(
            "owner = %s AND product IS NULL AND name = %s"
            % sqlvalues(database.Person.byName('testuser').id, 'test-branch'))

        self.assertEqual(None, branch.url)
        # If we get this far, the branch has been correctly inserted into the
        # database.


from canonical.launchpad.daemons import tachandler
import os
import shutil

class SFTPSetup(tachandler.TacTestSetup):
    root = '/tmp/sftp-test'
    tacfile = '/home/andrew/warthogs/supermirrorsftp/devel/supermirrorsftp/tests/test.tac'
    pidfile = root + '/twistd.pid'
    logfile = root + '/twistd.log'
    def setUpRoot(self):
        if os.path.isdir(self.root):
            shutil.rmtree(self.root)
        os.makedirs(self.root, 0700)

class TestSFTPServer:
    """This is the object returned by start_test_sftp_server."""
    # XXX: stub implementation for now.
    base = 'sftp://testuser@localhost:22222/'

    def __init__(self):
        #import os
        #os.system('cd ..; SUPERMIRROR_PORT=22222 PYTHONPATH=%s
        #/home/andrew/svn/Twisted/bin/twistd -oy
        #/home/andrew/warthogs/supermirrorsftp/devel/sftp.tac' 
        #    % os.environ.get('PYTHONPATH', ''))
        self.sftp = SFTPSetup()
        self.sftp.setUp()

    def stop(self):
        #import os
        #os.kill(int(open('twistd.pid', 'r').read()))
        self.sftp.tearDown()

    last_accessed_branch_id = -1




from bzrlib.commands import Command, Option
from bzrlib.errors import (BzrCommandError, NotBranchError, DivergedBranches,
    NoWorkingTree)
from bzrlib.branch import Branch
from bzrlib.trace import warning, note
class cmd_push(Command):
    """Push this branch into another branch.
    
    The remote branch will not have its working tree populated because this
    is both expensive, and may not be supported on the remote file system.
    
    Some smart servers or protocols *may* put the working tree in place.

    If there is no default push location set, the first push will set it.
    After that, you can omit the location to use the default.  To change the
    default, use --remember.

    This command only works on branches that have not diverged.  Branches are
    considered diverged if the branch being pushed to is not an older version
    of this branch.

    If branches have diverged, you can use 'bzr push --overwrite' to replace
    the other branch completely.
    
    If you want to ensure you have the different changes in the other branch,
    do a merge (see bzr help merge) from the other branch, and commit that
    before doing a 'push --overwrite'.
    """
    takes_options = ['remember', 'overwrite', 
                     Option('create-prefix', 
                            help='Create the path leading up to the branch '
                                 'if it does not already exist')]
    takes_args = ['location?']

    def run(self, location=None, remember=False, overwrite=False,
            create_prefix=False, verbose=False):
        # FIXME: Way too big!  Put this into a function called from the
        # command.
        import errno
        from shutil import rmtree
        from bzrlib.transport import get_transport
        
        tree_from = WorkingTree.open_containing(u'.')[0]
        br_from = tree_from.branch
        stored_loc = tree_from.branch.get_push_location()
        if location is None:
            if stored_loc is None:
                raise BzrCommandError("No push location known or specified.")
            else:
                print "Using saved location: %s" % stored_loc
                location = stored_loc
        try:
            br_to = Branch.open(location)
        except NotBranchError:
            # create a branch.
            transport = get_transport(location).clone('..')
            if not create_prefix:
                try:
                    transport.mkdir(transport.relpath(location))
                except NoSuchFile:
                    raise BzrCommandError("Parent directory of %s "
                                          "does not exist." % location)
            else:
                current = transport.base
                needed = [(transport, transport.relpath(location))]
                while needed:
                    try:
                        transport, relpath = needed[-1]
                        transport.mkdir(relpath)
                        needed.pop()
                    except NoSuchFile:
                        new_transport = transport.clone('..')
                        needed.append((new_transport,
                                       new_transport.relpath(transport.base)))
                        if new_transport.base == transport.base:
                            raise BzrCommandError("Could not creeate "
                                                  "path prefix.")
            br_to = Branch.initialize(location)
        old_rh = br_to.revision_history()
        try:
            try:
                tree_to = br_to.working_tree()
            except NoWorkingTree:
                # TODO: This should be updated for branches which don't have a
                # working tree, as opposed to ones where we just couldn't 
                # update the tree.
                warning('Unable to update the working tree of: %s' % (br_to.base,))
                count = br_to.pull(br_from, overwrite)
            else:
                count = tree_to.pull(br_from, overwrite)
        except DivergedBranches:
            raise BzrCommandError("These branches have diverged."
                                  "  Try a merge then push with overwrite.")
        if br_from.get_push_location() is None or remember:
            br_from.set_push_location(location)
        note('%d revision(s) pushed.' % (count,))

        if verbose:
            new_rh = br_to.revision_history()
            if old_rh != new_rh:
                # Something changed
                from bzrlib.log import show_changed_revisions
                show_changed_revisions(br_to, old_rh, new_rh)


def test_suite():
    loader = unittest.TestLoader()
    result = loader.loadTestsFromName(__name__)
    return result

