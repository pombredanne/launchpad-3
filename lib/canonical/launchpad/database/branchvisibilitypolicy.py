# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Implementation for the BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityTeamPolicy',
    'BranchVisibilityPolicyMixin',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.cachedproperty import cachedproperty

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    IBranchVisibilityTeamPolicy, IProduct, IProject)


class BranchVisibilityTeamPolicy(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityTeamPolicy)
    _table = 'BranchVisibilityPolicy'

    project = ForeignKey(dbName='project', foreignKey='Project')
    product = ForeignKey(dbName='product', foreignKey='Product')
    team = ForeignKey(dbName='team', foreignKey='Person', default=None)
    policy = EnumCol(
        schema=BranchVisibilityPolicy, notNull=True,
        default=BranchVisibilityPolicy.PUBLIC)


def policy_item_key(item):
    if item.team is None:
        return None
    return item.team.displayname


class BranchVisibilityPolicyMixin:
    """Specifies a list of branch visibility policy items."""

    @cachedproperty
    def _policy_visibility_context(self):
        if IProject.providedBy(self):
            return dict(project=self, product=None)
        elif IProduct.providedBy(self):
            return dict(project=None, product=self)
        else:
            raise AssertionError(
                "%s doesn't implement IProject nor IProduct." % self)

    @property
    def _policy_items(self):
        return BranchVisibilityTeamPolicy.selectBy(
            **self._policy_visibility_context)

    @property
    def branch_visibility_team_policies(self):
        """See IHasBranchVisibilityPolicy."""
        # If we are using the inherited policy return the items
        # from the inherited context.
        if self.isUsingInheritedBranchVisibilityPolicy():
            return self.project.branch_visibility_team_policies
        # Use shortlist here for policy items as we don't expect
        # many items, and want a warning emitted if we start
        # getting many items being created for projects as it
        # may indicate a design flaw.
        items = shortlist(self._policy_items)
        return sorted(items, key=policy_item_key)

    def _selectOneBranchVisibilityTeamPolicy(self, team):
        """Finds one particular policy item."""
        if self.isUsingInheritedBranchVisibilityPolicy():
            policy_visibility_context = self.project._policy_visibility_context
        else:
            policy_visibility_context = self._policy_visibility_context
        return BranchVisibilityTeamPolicy.selectOneBy(
                team=team, **policy_visibility_context)

    @property
    def branch_visibility_base_policy(self):
        """See IHasBranchVisibilityPolicy."""
        item = self._selectOneBranchVisibilityTeamPolicy(None)
        # If there is no explicit item set, then public is the default.
        if item is None:
            return BranchVisibilityPolicy.PUBLIC
        else:
            return item.policy

    def getBranchVisibilityPolicyForTeam(self, team):
        """See IHasBranchVisibilityPolicy."""
        item = self._selectOneBranchVisibilityTeamPolicy(team)
        if item is None:
            return None
        else:
            return item.policy

    def isUsingInheritedBranchVisibilityPolicy(self):
        """See IHasBranchVisibilityPolicy."""
        # If there is no project to inherit a policy from,
        # then we cannot be using an inherited policy.
        if getattr(self, 'project', None) is None:
            return False
        # If there are no explictly defined policy items, use the
        # inherited policy.
        return self._policy_items.count() == 0

    def setTeamBranchVisibilityPolicy(self, team, policy):
        """See IHasBranchVisibilityPolicy."""
        item = BranchVisibilityTeamPolicy.selectOneBy(
            team=team, **self._policy_visibility_context)
        if item is None:
            item = BranchVisibilityTeamPolicy(
                team=team, policy=policy, **self._policy_visibility_context)
        else:
            item.policy = policy

    def removeTeamFromBranchVisibilityPolicy(self, team):
        """See IHasBranchVisibilityPolicy."""
        item = BranchVisibilityTeamPolicy.selectOneBy(
            team=team, **self._policy_visibility_context)
        if item is not None:
            BranchVisibilityTeamPolicy.delete(item.id)
