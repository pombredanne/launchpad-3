# Copyright 2007 Canonical Ltd.  All rights reserved.

"""The interface for branch landing targets."""

__metaclass__ = type
__all__ = [
    'InvalidBranchLandingTarget',
    'IBranchLandingTarget',
    'IBranchLandingTargetSet',
    ]

from zope.interface import Interface
from zope.schema import Choice, Datetime

from canonical.launchpad import _


class InvalidBranchLandingTarget(Exception):
    """Raised during the creation of a new branch landing target.

    The text of the exception is the rule violation.
    """


class IBranchLandingTarget(Interface):
    """Branch landing targets show intent of landing one branch on another."""

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

    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)


class IBranchLandingTargetSet(Interface):
    """The set of defined landing targets."""

    def new(registrant, source_branch, target_branch):
        """Create a new branch landing target.

        Both the source and target branches must have valid products, and those
        products must be the same.

        There cannot already be a branch landing target defined for the source
        branch and target branch pair.
        """
