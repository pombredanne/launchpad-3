# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""Branch merge queues contain queued branch merge proposals."""

__metaclass__ = type
__all__ = [
    'IBranchMergeQueue',
    'IBranchMergeQueueSet',
    'IMultiBranchMergeQueue',
    ]


from zope.interface import Attribute, Interface
from zope.schema import TextLine, Datetime

from canonical.launchpad import _
from canonical.launchpad.fields import PublicPersonChoice, Summary
from canonical.launchpad.validators.name import name_validator


class IBranchMergeQueue(Interface):
    """The queued branch merge proposals for one or more branches."""

    branches = Attribute("The branches that this queue is for.")

    items = Attribute("The ordered queued branch merge proposals.")


class IMultiBranchMergeQueue(IBranchMergeQueue):
    """A queue that has proposals from a number of branches."""

    name = TextLine(
        title=_('Name'), required=True, constraint=name_validator,
        description=_("""At least one lowercase letter or number, followed by
            letters, dots, hyphens or plusses.
            Keep this name short, as it is used in URLs."""))

    summary = Summary(title=_('Summary'), required=False,
        description=_('Details about the purpose of the merge queue.'))

    registrant = PublicPersonChoice(
        title=_('Registrant'), required=True, readonly=True,
        vocabulary='ValidPersonOrTeam',
        description=_("Either yourself or a team you are a member of. "
                      "This controls who can modify the queue."))

    owner = PublicPersonChoice(
        title=_('Owner'), required=True,
        vocabulary='PersonActiveMembershipPlusSelf',
        description=_("Either yourself or a team you are a member of. "
                      "This controls who can manipulate the queue."))

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)


class IBranchMergeQueueSet(Interface):
    """A utility interface for getting merge queues."""

    def getByName(queue_name):
        """Return the BranchMergeQueue with the specified name.

        :param queue_name: The name of the multi-branch merge queue.
        :type queue_name: String.
        :raises NotFoundError: if a queue with the specified name does not
            exist.
        """

    def getForBranch(branch):
        """Get a `BranchMergeQueue` for the specified branch.

        If the branch has defined that the queue for the branch is a
        multi-branch queue, then that queue is returned.

        :param branch: The branch to get the queue for.
        :type branch: `IBranch`.
        :raises NotUsingBranchMergeQueues: If the branch has said that it is
            not using Launchpad merge queues, an exception.
        """

    def newMultiBranchMergeQueue(registrant, owner, name, summary):
        """Create a new `MultiBranchMergeQueue`."""
