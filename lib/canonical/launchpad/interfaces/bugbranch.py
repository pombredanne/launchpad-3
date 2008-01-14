# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces for linking BugTasks and Branches."""

__metaclass__ = type

__all__ = [
    "BugBranchStatus",
    "IBugBranch",
    "IBugBranchSet",
    ]

from zope.interface import Interface
from zope.schema import Choice, Int, Object, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import BugField
from canonical.launchpad.interfaces import (
    IHasBug, IHasDateCreated, non_duplicate_branch)
from canonical.launchpad.interfaces.bugtask import IBugTask
from canonical.launchpad.interfaces.person import IPerson

from canonical.lazr import DBEnumeratedType, DBItem


class BugBranchStatus(DBEnumeratedType):
    """The status of a bugfix branch."""

    ABANDONED = DBItem(10, """
        Abandoned Attempt

        A fix for this bug is no longer being worked on in this
        branch.
        """)

    INPROGRESS = DBItem(20, """
        Fix In Progress

        Development to fix this bug is currently going on in this
        branch.
        """)

    FIXAVAILABLE = DBItem(30, """
        Fix Available

        This branch contains a potentially useful fix for this bug.
        """)

    BESTFIX = DBItem(40, """
        Best Fix Available

        This branch contains a fix agreed upon by the community as
        being the best available branch from which to merge to fix
        this bug.
        """)


class IBugBranch(IHasDateCreated, IHasBug):
    """A branch linked to a bug."""

    id = Int(title=_("Bug Branch #"))
    bug = BugField(
        title=_("The bug that is linked to."), required=True, readonly=True)
    branch = Choice(
        title=_("Branch"), vocabulary="Branch",
        constraint=non_duplicate_branch, required=True, readonly=True)
    revision_hint = TextLine(title=_("Revision Hint"))
    status = Choice(
        title=_("State"), vocabulary=BugBranchStatus,
        default=BugBranchStatus.INPROGRESS)
    whiteboard = Text(
        title=_('Status Whiteboard'), required=False,
        description=_(
            'Additional information about the status of the bugfix '
            'in this branch.'))

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
