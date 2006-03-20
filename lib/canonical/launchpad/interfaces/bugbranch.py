# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Interfaces for linking BugTasks and Branches."""

__metaclass__ = type

__all__ = [
    "IBugBranch",
    "IBugBranchAddForm"]

from zope.interface import Interface
from zope.schema import Int, Text, TextLine, Choice

from canonical.lp.dbschema import BugBranchStatus
from canonical.launchpad.interfaces import IHasDateCreated, non_duplicate_branch
from canonical.launchpad import _

class IBugBranch(IHasDateCreated):
    id = Int(title=_("Bug Branch #"))
    bug = Int(title=_("Bug"))
    branch = Choice(
        title=_("Branch"), vocabulary="ProductBranch",
        constraint=non_duplicate_branch)
    fixed_in_revision_id = TextLine(title=_("Revision ID"))
    status = Choice(
        title=_("State"), vocabulary="BugBranchStatus",
        default=BugBranchStatus.UNDERDEVELOPMENT)


class IBugBranchAddForm(IBugBranch):
    comment = Text(title=_("Comment"), required=False)
