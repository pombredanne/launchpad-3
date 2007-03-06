# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BugBranchRevision interfaces."""

__metaclass__ = type
__all__ = ['IBugBranchRevision', 'IBugBranchRevisionSet']

from zope.interface import Interface, Attribute
from zope.schema import Int

from canonical.launchpad import _


class IBugBranchRevision(Interface):
    """The association between a bug and a revision of a branch."""

    id = Int(title=_('The database ID'))

    bug = Attribute("The bug that relates to the revision.")
    branch = Attribute("The branch that the revision occurs in.")
    revision = Attribute("The revision that relates to the bug.")


class IBugBranchRevisionSet(Interface):
    """The set of all bug-revision associations."""

    def new(bug, branch, revision):
        """Create a new BugBranchRevision for the specified bug, branch and
        revision."""

