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
    def _policy_visibility_key(self):
        product, project = None, None
        if IProject.providedBy(self):
            project = self
        elif IProduct.providedBy(self):
            product = self
        assert product or project, (
            "One of product or project must not be None")
        return {'product':product, 'project':project}

    @property
    def _policy_items(self):
        return BranchVisibilityPolicyItem.selectBy(
            **self._policy_visibility_key)

    @property
    def branch_visibility_policy_items(self):
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

    def isUsingInheritedBranchVisibilityPolicy(self):
        """See IBranchVisibilityPolicy."""
        # If there is no project to inherit a policy from,
        # then we cannot be using an inherited policy.
        if getattr(self, 'project', None) is None:
            return False
        # If there are no explictly defined policy items, use the
        # inherited policy.
        return self._policy_items.count() == 0

    def setTeamBranchVisibilityPolicy(self, team, policy):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            team=team, **self._policy_visibility_key)
        if item is None:
            item = BranchVisibilityPolicyItem(
                team=team, policy=policy, **self._policy_visibility_key)
        else:
            item.policy = policy

    def removeTeamFromBranchVisibilityPolicy(self, team):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            team=team, **self._policy_visibility_key)
        if item is not None:
            BranchVisibilityPolicyItem.delete(item.id)
