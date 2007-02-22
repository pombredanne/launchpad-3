# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchRevision interfaces."""

__metaclass__ = type
__all__ = ['IBranchRevision', 'IBranchRevisionSet']

from zope.interface import Interface, Attribute
from zope.schema import Int

from canonical.launchpad import _


class IBranchRevision(Interface):
    """The association between a revision and a branch."""

    sequence = Int(
        title=_("Revision Number"), required=True,
        description=_("The index of a revision within a branch's history."))
    branch = Attribute("The branch this revision number belongs to.")
    revision = Attribute("The revision with that index in this branch.")

    # NOMERGE: Rephrase this to account for merged revisions.

class IBranchRevisionSet(Interface):
    """The set of all branch revisions."""

    def new(branch, sequence, revision):
        """Create a new BranchRevision for the specified branch."""

    def delete(branch_revision_id):
        """Delete the BranchRevision."""

    # NOMERGE: remove that from the interface, we do not want non-test code
    # to use it ever! Move the docstring into the content class.
    def getAncestryForBranch(branch):
        """Returns an unordered list of all BranchRevisions for a branch."""

    def getRevisionHistoryForBranch(branch, limit=None):
        """Returns an ordered list of at most limit BranchRevisions.

        If limit is omitted, then all the BranchRevisions for the branch
        are returned.
        
        They are ordered with the most recent revision first, and the list
        only contains those in the "leftmost tree", or in other words
        the revisions that match the revision history from bzrlib for this
        branch.
        """
