# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Acceptance tests for Supermirror SFTP server's bzr support.
"""

__metaclass__ = type

import unittest

import bzrlib

from canonical.launchpad.database.branch import Branch as lpBranch

class AcceptanceTests(unittest.TestCase):
    """ 
    These are the agreed acceptance tests for the Supermirror SFTP system's
    initial implementation of bzr support, converted from the English at
    https://wiki.launchpad.canonical.com/SupermirrorTaskList
    """

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
        
        # set up test branch
        local_path = xxx
        local_branch = make_new_branch(local_path) # bzr init; echo hello > world.txt; bzr add; bzr ci -m "test."
        
        # start test server
        remote_prefix = start_test_sftp_server()
        remote_path = remote_prefix + '~testuser/+junk/test-branch'
        
        # bzr push works
        bzr_push(local_branch, remote_path) # expect no errors
        
        # bzr log works
        self.assertEqual(bzr_log(local_path), bzr_log(remote_path))

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
        # set up test branch
        local_path = xxx
        local_branch = make_new_branch(local_path) # bzr init; echo hello > world.txt; bzr add; bzr ci -m "test."

        # start test server
        remote_prefix = start_test_sftp_server()

        # cannot push branches to products that don't exist
        self.assertRaises(
            PermissionError, 
            bzr_push, 
            local_branch, remote_prefix + '~testuser/fake-product/hello')

        # teams cannot have +junk products
        self.assertRaises(
            PermissionError,
            bzr_push, 
            local_branch, remote_prefix + '~testteam/+junk/hello')

        # cannot push to team directories that the user isn't a member of
        self.assertRaises(
            PermissionError,
            bzr_push, 
            local_branch, remote_prefix + '~not-my-team/real-product/hello')

        # XXX: what about lp-incompatible branch dir names (e.g. capital
        # letters) -- Are they disallowed or accepted?


    def test_3_rename_branch(self)
        """
        Branches should be able to be renamed in the Launchpad webapp, and those
        renames should be immediately reflected in subsequent SFTP connections.
        """

        # set up test branch
        local_path = xxx
        local_branch = make_new_branch(local_path) # bzr init; echo hello > world.txt; bzr add; bzr ci -m "test."
        
        # start test server
        remote_prefix = start_test_sftp_server()
        remote_path = remote_prefix + '~testuser/+junk/test-branch'
        
        # bzr push
        bzr_push(local_branch, remote_path) # expect no errors

        # rename branch in the webapp
        # XXX: should really be a page test here.
        lp_txn.begin()
        branch = lpBranch.selectOneBy(name='test-branch')
        branch.name = 'renamed-branch'
        lp_txn.commit()

        # compare bzr log output to compare branches
        remote_path = remote_prefix + '~testuser/+junk/renamed-branch'
        self.assertEqual(bzr_log(local_path), bzr_log(remote_yypath))

    def test_4_url_for_mirror(self):
        """
        There should be an API that can generate a URL for a branch for
        copy-to-mirror script to use. For example, for a branch with a database
        ID of 0xabcdef12, the URL may be something like
        `/srv/supermirrorsftp/branches/ab/cd/ef/12`.
        """
        # push branch to sftp server
        branch_id = push_branch_to_sftp_server() # similar boilerplate to 1,2,3?

        # generate the path for copy-to-mirror script to use
        mirror_from_path = get_path_for_copy_to_mirror(branch_id)

        # check that it's the branch we're looking for
        self.assertEqual(bzr_log(local_path), bzr_log(mirror_from_path))
        
    def test_5_mod_rewrite_data(self):
        """
        A mapping file for use with Apache's mod_rewrite should be generated
        correctly.
        """
        # push branch to sftp server
        branch_id = push_branch_to_sftp_server() # similar boilerplate to 1,2,3,4?

        # ... boilerplate ...

        # check the generated mapping file has the right contents        
        self.assertEqual(
            '~testuser/+junk/test-branch %d\n' % branch_id,
            generate_path_mapping([branch_id]))


