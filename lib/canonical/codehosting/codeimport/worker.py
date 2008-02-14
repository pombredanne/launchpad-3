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


def ensure_base(transport):
    try:
        transport.ensure_base()
    except NoSuchFile:
        create_prefix(transport)


class BazaarBranchStore:
    """A place where Bazaar branches of code imports are kept."""

    def __init__(self, transport):
        """Construct a Bazaar branch store based at `transport`."""
        self.transport = transport

    def _getMirrorURL(self, code_import):
        return urljoin(self.transport.base, '%08x' % code_import.branch.id)

    def pull(self, code_import, target_path):
        """Pull down the Bazaar branch for `code_import` to `target_path`.

        :return: A Bazaar working tree for the branch of `code_import`.
        """
        try:
            bzr_dir = BzrDir.open(self._getMirrorURL(code_import))
        except NotBranchError:
            return BzrDir.create_standalone_workingtree(target_path)
        bzr_dir.sprout(target_path)
        return BzrDir.open(target_path).open_workingtree()

    def push(self, code_import, bzr_tree):
        """Push up `bzr_tree` as the Bazaar branch for `code_import`."""
        ensure_base(self.transport)
        branch_from = bzr_tree.branch
        target_url = self._getMirrorURL(code_import)
        try:
            branch_to = Branch.open(target_url)
        except NotBranchError:
            branch_to = BzrDir.create_branch_and_repo(target_url)
        branch_to.pull(branch_from)


def get_default_bazaar_branch_store():
    """Return the default `BazaarBranchStore`."""
    return BazaarBranchStore(
        get_transport(config.codeimport.bazaar_branch_store))
