# Copyright 2008 Canonical Ltd.  All rights reserved.

"""The code import worker. This imports code from foreign repositories."""

__metaclass__ = type
__all__ = ['BazaarBranchStore', 'get_default_bazaar_branch_store']


from bzrlib.branch import Branch
from bzrlib.builtins import _create_prefix as create_prefix
from bzrlib.bzrdir import BzrDir
from bzrlib.transport import get_transport
from bzrlib.errors import NoSuchFile, NotBranchError
from bzrlib.urlutils import join as urljoin

from canonical.config import config
from canonical.launchpad.interfaces import BranchType, BranchTypeError


def ensure_base(transport):
    """Make sure that the base directory of `transport` exists.

    If the base directory does not exist, try to make it. If the parent of the
    base directory doesn't exist, try to make that, and so on.
    """
    try:
        transport.ensure_base()
    except NoSuchFile:
        create_prefix(transport)


class BazaarBranchStore:
    """A place where Bazaar branches of code imports are kept."""

    # This code is intended to replace c.codehosting.codeimport.publish and
    # canonical.codeimport.codeimport.gettarget.

    def __init__(self, transport):
        """Construct a Bazaar branch store based at `transport`."""
        self.transport = transport

    def _checkBranchIsImported(self, db_branch):
        """Raise `BranchTypeError` if `db_branch` not an imported branch."""
        if db_branch.branch_type != BranchType.IMPORTED:
            raise BranchTypeError(
                "Can only store imported branches: %r is of type %r."
                % (db_branch, db_branch.branch_type))

    def _getMirrorURL(self, db_branch):
        """Return the URL that `db_branch` is stored at."""
        return urljoin(self.transport.base, '%08x' % db_branch.id)

    def pull(self, db_branch, target_path):
        """Pull down the Bazaar branch for `code_import` to `target_path`.

        :return: A Bazaar working tree for the branch of `code_import`.
        """
        self._checkBranchIsImported(db_branch)
        try:
            bzr_dir = BzrDir.open(self._getMirrorURL(db_branch))
        except NotBranchError:
            return BzrDir.create_standalone_workingtree(target_path)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def push(self, db_branch, bzr_tree):
        """Push up `bzr_tree` as the Bazaar branch for `code_import`."""
        self._checkBranchIsImported(db_branch)
        ensure_base(self.transport)
        branch_from = bzr_tree.branch
        target_url = self._getMirrorURL(db_branch)
        try:
            branch_to = Branch.open(target_url)
        except NotBranchError:
            branch_to = BzrDir.create_branch_and_repo(target_url)
        branch_to.pull(branch_from)


def get_default_bazaar_branch_store():
    """Return the default `BazaarBranchStore`."""
    return BazaarBranchStore(
        get_transport(config.codeimport.bazaar_branch_store))
