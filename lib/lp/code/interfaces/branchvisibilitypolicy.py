# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'IHasBranchVisibilityPolicy',
    'IBranchVisibilityTeamPolicy',
    'InvalidVisibilityPolicy',
    ]

from zope.interface import Interface
from zope.schema import Choice

from canonical.launchpad import _
from lp.code.enums import TeamBranchVisibilityRule
from lp.services.fields import PersonChoice


class InvalidVisibilityPolicy(Exception):
    """The default policy can only be public or forbidden.

    If an attempt is made to set it to something other than one of these two
    values, this exception is raised.
    """


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

    def getBranchVisibilityRuleForBranch(branch):
        """Return the most specific visibility rule for a branch.

        The owner of the branch is used to determine the team that the rule
        applies to.  If there is a rule defined for the actual branch owner
        then that rule is used in preference to other rules only applicable
        through team membership.

        If there are a number of rules that apply for the owner of the branch
        then the most restrictive rule is retuned.
        """

    def isUsingInheritedBranchVisibilityPolicy():
        """Return True if using policy from the inherited context.

        Products that don't have any explicitly defined team policies, use
        the team policies defined for the project if the product has an
        associated project.  ProjectGroups can't have inherited policies.
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
    """A branch visibility team policy is defined as a team and a rule.

    The team may be null, in which case the rule applies to everyone.
    """

    team = PersonChoice(
        title=_('Team'), required=True, vocabulary='ValidPersonOrTeam',
        description=_("Specifies the team that the policy applies to. "
                      "If None then the policy applies to everyone."))

    rule = Choice(
        title=_('Rule'), vocabulary=TeamBranchVisibilityRule,
        default=TeamBranchVisibilityRule.PUBLIC,
        description=_(
        "The visibility rule defines the default branch visibility for "
        "members of the team specified."))
