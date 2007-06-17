# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'IHasBranchVisibilityPolicy',
    'IBranchVisibilityTeamPolicy',
    ]

from zope.interface import Interface, Attribute

from zope.schema import Choice

from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad import _


class IHasBranchVisibilityPolicy(Interface):
    """Implemented by types that need to define default branch visibility."""

    branch_visibility_team_policies = Attribute(
        "The branch visibility policy items.")

    branch_visibility_base_policy = Attribute(
        "The BranchVisibilityPolicy that applies to everyone.")

    def getBranchVisibilityPolicyForTeam(team):
        """Return the defined policy for the team.

        If there is no explicit policy set for the team, return None.
        """

    def isUsingInheritedBranchVisibilityPolicy():
        """Return True if using policy from the inherited context.

        BranchVisibilityPolicy objects for products are constructed with the
        BranchVisibilityPolicy objects of their projects if they have a
        project.  Projects can't have inherited policies.
        """

    def setTeamBranchVisibilityPolicy(team, policy):
        """Set the policy for the team.

        Each team can only have one policy.
        """

    def removeTeamFromBranchVisibilityPolicy(team):
        """Remove the team from the policy list.

        If the team exists in the items list it is removed.  If the team
        isn't in the items list, the method returns and the state of the
        object is unchanged.  Attempting to remove the team None returns
        the policy for everyone back to the default, which is Public.
        """


class IBranchVisibilityTeamPolicy(Interface):
    """A branch visibility team policy is defined as a team and a policy.

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
