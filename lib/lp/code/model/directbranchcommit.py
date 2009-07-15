# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Commit files straight to bzr branch."""

__metaclass__ = type
__all__ = [
    'ConcurrentUpdateError',
    'DirectBranchCommit',
    ]


import os.path

from bzrlib.branch import Branch as BzrBranch
from bzrlib.generate_ids import gen_file_id
from bzrlib.revision import NULL_REVISION
from bzrlib.transform import TransformPreview

from lp.codehosting.vfs import get_multi_server


class ConcurrentUpdateError(Exception):
    """Bailout exception for concurrent updates.

    This is raised when committing to a branch would risk overwriting
    concurrent changes made by another party.
    """


class DirectBranchCommit:
    """Commit a set of files straight into a branch.

    Use this to write a set of files into a branch efficiently, without
    caring what was in there before.  The files may be new to the branch
    or they may exist there already; in the latter case they will be
    overwritten.

    The branch is write-locked for the entire lifetime of this object.
    Be sure to call unlock() when done.  This will be done for you as
    part of a successful commit, but unlocking more than once will do no
    harm.

    The trick for this was invented by Aaron Bentley.  It saves having
    to do a full checkout of the branch.
    """
    is_open = False
    is_locked = False

    def __init__(self, db_branch, committer=None, bzrserver=None):
        """Create context for direct commit to branch.

        :param db_branch: a Launchpad `Branch` object.
        :param committer: the `Person` writing to the branch.
        :param bzrserver: an optional bzr server to use.  You can set
            one up using `DirectBranchCommit.makeBzrServer`, use it as
            many times as you like, then tear it down.  Or you can omit
            this parameter and one will be created (and torn down) for
            you.
        """
        self.db_branch = db_branch

        if bzrserver is None:
            self.bzrserver = self.makeBzrServer()
            self.own_bzrserver = True
        else:
            self.bzrserver = bzrserver
            self.own_bzrserver = False

        if committer is None:
            committer = db_branch.owner
        self.committer = committer

        #mirrorer = BranchMirrorer(HostedBranchPolicy(), None, None)
        mirrorer = BzrBranch
        self.bzrbranch = mirrorer.open(self.db_branch.getPullURL())
        self.bzrbranch.lock_write()
        self.is_locked = True

        try:
            self.revision_tree = self.bzrbranch.basis_tree()
            self.transform_preview = TransformPreview(self.revision_tree)

            self.is_open = True
        except:
            self.unlock()
            self.is_locked = False
            raise

        self.files = set()

    @classmethod
    def makeBzrServer(cls):
        """Create a bzr server to use with one or more `DirectBranchCommit`s.

        Invoke tearDown on the server when you're done with it.  Thank you.
        """
        server = get_multi_server(write_hosted=True)
        server.setUp()
        return server

    def _getDir(self, path):
        """Get trans_id for directory "path."  Create if necessary."""
        dir = self.revision_tree.path2id(path)
        if dir:
            return self.transform_preview.trans_id_tree_path(path)

        parent_dir, dirname = os.path.split(path)
        if dirname:
            parent_id = self._getDir(parent_dir)
        else:
            parent_id = None

        dirfile_id = gen_file_id(path)
        return self.transform_preview.new_directory(
            dirname, parent_id, dirfile_id)

    def writeFile(self, path, contents):
        """Write file to branch; may be an update or a new file.

        If you write a file multiple times, the first one is used and
        the rest ignored.
        """
        assert self.is_open, "Writing file to closed DirectBranchCommit."

        if path in self.files:
            # We already have this file.  Ignore second write.
            return

        file_id = self.revision_tree.path2id(path)
        if file_id is None:
            parent_path, name = os.path.split(path)
            parent_id = self._getDir(parent_path)
            file_id = gen_file_id(name)
            self.transform_preview.new_file(
                name, parent_id, [contents], file_id)
        else:
            trans_id = self.transform_preview.trans_id_tree_path(path)
            # Delete old contents.  It doesn't actually matter whether
            # we do this before creating the new contents.
            self.transform_preview.delete_contents(trans_id)
            self.transform_preview.create_file([contents], trans_id)

        self.files.add(path)

    def _checkForRace(self):
        """Check if bzrbranch has any changes waiting to be scanned.

        If it does, raise `ConcurrentUpdateError`.
        """
        assert self.is_locked, "Getting revision on un-locked branch."
        last_revision = None
        last_revision = self.bzrbranch.last_revision()
        if last_revision != self.db_branch.last_scanned_id:
            raise ConcurrentUpdateError(
                "Branch has been changed.  Not committing.")

    def commit(self, commit_message):
        """Commit to branch."""
        assert self.is_open, "Committing closed DirectBranchCommit."
        assert self.is_locked, "Not locked at commit time."

        try:
            self._checkForRace()

            preview_tree = self.transform_preview.get_preview_tree()

            rev_id = self.revision_tree.get_revision_id()
            if rev_id == NULL_REVISION:
                parents = []
            else:
                parents = [rev_id]

            builder = self.bzrbranch.get_commit_builder(parents)

            list(builder.record_iter_changes(
                preview_tree, rev_id, self.transform_preview.iter_changes()))

            builder.finish_inventory()

            new_rev_id = builder.commit(commit_message)

            revno, old_rev_id = self.bzrbranch.last_revision_info()
            self.bzrbranch.set_last_revision_info(revno + 1, new_rev_id)

        finally:
            self.unlock()
            self.is_open = False

    def unlock(self):
        """Release commit lock, if held."""
        if self.is_locked:
            self.bzrbranch.unlock()
            self.is_locked = False

        if self.own_bzrserver:
            self.bzrserver.tearDown()
            self.bzrserver = None
            self.own_bzrserver = False
