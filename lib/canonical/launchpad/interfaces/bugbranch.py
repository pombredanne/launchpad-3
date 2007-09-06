# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for linking BugTasks and Branches."""

__metaclass__ = type

__all__ = ["IBugBranch",
           "IBugBranchSet"]

from zope.interface import Interface
from zope.schema import Int, Text, TextLine, Choice

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IHasDateCreated, non_duplicate_branch, IHasBug)
from canonical.lp.dbschema import BugBranchStatus


class IBugBranch(IHasDateCreated, IHasBug):
    """A branch linked to a bug."""

    id = Int(title=_("Bug Branch #"))
    bug = Int(title=_("Bug"))
    branch = Choice(
        title=_("Branch"), vocabulary="Branch",
        constraint=non_duplicate_branch)
    revision_hint = TextLine(title=_("Revision Hint"))
    status = Choice(
        title=_("State"), vocabulary="BugBranchStatus",
        default=BugBranchStatus.INPROGRESS)
    whiteboard = Text(
        title=_('Status Whiteboard'), required=False,
        description=_(
            'Additional information about the status of the bugfix '
            'in this branch.'))

class IBugBranchSet(Interface):

    def getBugBranchesForBranches(branches):
        """Return a sequence of IBugBranch instances associated with
        the given branches."""

    def getBugBranchesForBugTasks(tasks):
        """Return a sequence of IBugBranch instances associated with
        the bugs for the given tasks."""

