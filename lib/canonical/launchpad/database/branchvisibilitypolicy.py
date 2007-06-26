# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Implementation for the BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityPolicyItem',
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
    IBranchVisibilityPolicyItem, IProduct, IProject)


class BranchVisibilityPolicyItem(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityPolicyItem)
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
        return BranchVisibilityPolicyItem.selectBy(
            **self._policy_visibility_context)

    @property
    def branch_visibility_policy_items(self):
        """See IHasBranchVisibilityPolicy."""
        # If we are using the inherited policy return the items
        # from the inherited context.
        if self.isUsingInheritedBranchVisibilityPolicy():
            return self.project.branch_visibility_policy_items
        # Use shortlist here for policy items as we don't expect
        # many items, and want a warning emitted if we start
        # getting many items being created for projects as it
        # may indicate a design flaw.
        items = shortlist(self._policy_items)
        return sorted(items, key=policy_item_key)

    @property
    def branch_visibility_base_policy(self):
        """See IHasBranchVisibilityPolicy."""
        if self.isUsingInheritedBranchVisibilityPolicy():
            item = BranchVisibilityPolicyItem.selectOneBy(
                team=None, **self.project._policy_visibility_context)
        else:
            item = BranchVisibilityPolicyItem.selectOneBy(
                team=None, **self._policy_visibility_context)

        # If there is no explicit item set, then public is the default.
        if item is None:
            return BranchVisibilityPolicy.PUBLIC
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
        item = BranchVisibilityPolicyItem.selectOneBy(
            team=team, **self._policy_visibility_context)
        if item is None:
            item = BranchVisibilityPolicyItem(
                team=team, policy=policy, **self._policy_visibility_context)
        else:
            item.policy = policy

    def removeTeamFromBranchVisibilityPolicy(self, team):
        """See IHasBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            team=team, **self._policy_visibility_context)
        if item is not None:
            BranchVisibilityPolicyItem.delete(item.id)
