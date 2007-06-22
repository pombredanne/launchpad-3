# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'IHasBranchVisibilityPolicy',
    'IBranchVisibilityTeamPolicy',
    ]

from zope.interface import Interface, Attribute

from zope.schema import Choice

from canonical.lp.dbschema import BranchVisibilityRule

from canonical.launchpad import _


class IHasBranchVisibilityPolicy(Interface):
    """Implemented by types that need to define default branch visibility."""

    def getBranchVisibilityTeamPolicies():
        """The branch visibility team policy items."""

    def getBaseBranchVisibilityRule():
        """Return the BranchVisibilityRule that applies to everyone."""

    def getBranchVisibilityRuleForTeam(team):
        """Return the defined visibility rule for the team.

        If there is no explicit team policy set for the team, return None.
        """

    def isUsingInheritedBranchVisibilityPolicy():
        """Return True if using policy from the inherited context.

        Products that don't have any explicitly defined team policies, use
        the team policies defined for the project if the product has an
        associated project.  Projects can't have inherited policies.
        """

    def setBranchVisibilityTeamPolicy(team, rule):
        """Set the policy for the team.

        Each team can only have one policy.

        :param team: The team to associate with the rule.
        :param rule: A value of the BranchVisibilityRule enumerated type.
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
        title=_('Policy'), vocabulary='BranchVisibilityRule',
        default=BranchVisibilityRule.PUBLIC,
        description=_(
        "The policy defines the default branch visibility for members of the "
        "team specified."))
