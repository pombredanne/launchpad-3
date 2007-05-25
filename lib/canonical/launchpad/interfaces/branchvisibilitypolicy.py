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

    items = Attribute("""
        A list of policy items.

        If there is a policy that does not have a team set, this
        policy item is returned as the first item of the sequence.
        """)

    context = Attribute("The object that the policy applies to")

    inherited_policy = Attribute("""
        An optional BranchVisibilityPolicy whose policy items are used
        when there are no explicit policy items set for the defined
        context.""")

    def isUsingInheritedPolicy():
        """Return True if using policy from the inherited context.

        BranchVisibilityPolicy objects for products are constructed with the
        BranchVisibilityPolicy objects of their projects if they have a
        project.  Projects can't have inherited policies.
        """

    def setTeamPolicy(team, policy):
        """Set the policy for the team.

        Each team can only have one policy.
        """

    def removeTeam(team):
        """Remove the team from the policy list.

        If the team exists in the items list it is removed.  If the team
        isn't in the items list, the method returns and the state of the
        object is unchanged.  Attempting to remove the team None returns
        the policy for everyone back to the default, which is Public.
        """
