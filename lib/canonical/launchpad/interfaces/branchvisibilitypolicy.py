# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'IHasBranchVisibilityPolicy',
    'IBranchVisibilityPolicyItem',
    'IBranchVisibilityPolicy',
    ]

from zope.interface import Interface, Attribute

from zope.schema import Choice

from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad import _


class IHasBranchVisibilityPolicy(Interface):
    """Implemented by types that need to define default branch visibility."""

    branch_visibility_policy = Attribute('The branch visibility policy')


class IBranchVisibilityPolicyItem(Interface):
    """A branch visibility policy item is defined as a team and a policy.

    The team may be null, in which case the policy applies to everyone.
    """
    
    team = Choice(
        title=_('Team'), required=False, vocabulary='ValidPersonOrTeam',
        description=_("Specifies the team that the policy applies to. "
                      "If None then the policy applies to everyone."))

    policy = Choice(
        title=_('Policy'), vocabulary='BranchVisibilityPolicy',
        default=BranchVisibilityPolicy.PUBLIC,
        description=_(
        "The policy defines the default branch visibility for members of the "
        "team specified."))


class IBranchVisibilityPolicy(Interface):
    """Specifies a list of branch visibility policy items."""

    policy_list = Attribute("A list of policy items")

    context = Attribute("The object that the policy applies to")

    def addTeam(team, policy):
        """Adds the team to the policy list with the specified policy.
        
        Raises an error if the team is already specified in this context.
        """
        
    def removeTeam(team):
        """Removes the team from the policy list.

        Raises an error if the team is not specified in this context.
        """

        
