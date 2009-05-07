# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking BugTasks and Branches."""

__metaclass__ = type

__all__ = [
    "IBugBranch",
    "IBugBranchSet",
    ]

from zope.interface import Interface
from zope.schema import Choice, Int, Object, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import BugField, Summary
from canonical.launchpad.interfaces import (
    IHasBug, IHasDateCreated, non_duplicate_branch)
from canonical.launchpad.interfaces.bugtask import IBugTask
from lp.registry.interfaces.person import IPerson


class IBugBranch(IHasDateCreated, IHasBug):
    """A branch linked to a bug."""

    id = Int(title=_("Bug Branch #"))
    bug = BugField(
        title=_("The bug that is linked to."),
        required=True, readonly=True)
    branch = Choice(
        title=_("Branch"), vocabulary="Branch",
        constraint=non_duplicate_branch, required=True, readonly=True)
    revision_hint = TextLine(title=_("Revision Hint"))

    bug_task = Object(
        schema=IBugTask, title=_("The bug task that the branch fixes"),
        description=_(
            "the bug task reported against this branch's product or the "
            "first bug task (in case where there is no task reported "
            "against the branch's product)."),
        readonly=True)

    registrant = Object(
        schema=IPerson, readonly=True, required=True,
        title=_("The person who linked the bug to the branch"))


class IBugBranchSet(Interface):

    def getBugBranch(bug, branch):
        """Return the BugBranch for the given bug and branch.

        Return None if there is no such link.
        """

    def getBugBranchesForBranches(branches, user):
        """Return a sequence of IBugBranch instances associated with
        the given branches.

        Only return instances that are visible to the user.
        """

    def getBugBranchesForBugTasks(tasks):
        """Return a sequence of IBugBranch instances associated with
        the bugs for the given tasks."""

    def new(bug, branch, status, registrant):
        """Create and return a new BugBranch."""
