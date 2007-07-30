# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The interface for branch merge proposals."""

__metaclass__ = type
__all__ = [
    'InvalidBranchMergeProposal',
    'IBranchMergeProposal',
    'IBranchMergeProposalSet',
    ]

from zope.interface import Interface
from zope.schema import Choice, Datetime

from canonical.launchpad import _


class InvalidBranchMergeProposal(Exception):
    """Raised during the creation of a new branch merge proposal.

    The text of the exception is the rule violation.
    """


class IBranchMergeProposal(Interface):
    """Branch merge proposals show intent of landing one branch on another."""

    registrant = Choice(
        title=_('Person'), required=True,
        vocabulary='ValidPersonOrTeam', readonly=True,
        description=_('The person who registered the landing target.'))

    source_branch = Choice(
        title=_('Source Branch'),
        vocabulary='Branch',
        readonly=True,
        description=_("The Bazaar branch that has code to land."))

    target_branch = Choice(
        title=_('Target Branch'),
        vocabulary='Branch',
        readonly=True,
        description=_("The Bazaar branch that the code will land on."))

    dependent_branch = Choice(
        title=_('Dependent Branch'),
        vocabulary='Branch',
        readonly=True,
        description=_("The Bazaar branch that the source branch branched from."))

    whiteboard = Whiteboard(
        title=_('Whiteboard'), required=False,
        description=_('Notes about the merge.'))

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)


class IBranchMergeProposalSet(Interface):
    """A central place to maintain all the rules for merge proposals."""

    def new(registrant, source_branch, target_branch,
            dependent_branch=None, whiteboard=None):
        """Create a new BranchMergeProposal."""
