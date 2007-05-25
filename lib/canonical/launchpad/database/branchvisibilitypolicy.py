# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityPolicyItem',
    'BranchVisibilityPolicy',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import (
    BranchVisibilityPolicy as BranchVisibilityPolicyEnum)

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces import (
    IBranchVisibilityPolicyItem, IBranchVisibilityPolicy)


class BranchVisibilityPolicyItem(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityPolicyItem)
    _table = 'BranchVisibilityPolicy'

    project = ForeignKey(dbName='project', foreignKey='Project')
    product = ForeignKey(dbName='product', foreignKey='Product')
    team = ForeignKey(dbName='team', foreignKey='Person', default=None)
    policy = EnumCol(
        schema=BranchVisibilityPolicyEnum, notNull=True,
        default=BranchVisibilityPolicyEnum.PUBLIC)


def policy_item_key(item):
    if item.team is None:
        return None
    return item.team.displayname


class BranchVisibilityPolicy:
    """Specifies a list of branch visibility policy items."""

    implements(IBranchVisibilityPolicy)

    def __init__(self, product=None, project=None, inherited_policy=None):
        # Exactly one of product or project should be not None.
        assert (product is None and project is not None or
                product is not None and project is None), (
            "Only one of product or project can be set")
        if product is not None:
            self.context = product
            self.product = product
            self.project = None
        else:
            self.context = project
            self.product = None
            self.project = project

        self.inherited_policy = inherited_policy

    @property
    def policy_items(self):
        # The query is shortlisted to demonstrate that we are only expecting a
        # few items, and to give warnings if too many items start appearing.
        if self.product is not None:
            query = "BranchVisibilityPolicy.product = %s" % self.product.id
        else:
            query = "BranchVisibilityPolicy.project = %s" % self.project.id
        return shortlist(BranchVisibilityPolicyItem.select(query))

    @property
    def items(self):
        # If we are using the inherited policy return the items
        # from the inherited context.
        if self.isUsingInheritedPolicy():
            return self.inherited_policy.items
        # Copy the policy_items list, don't just get a reference to it.
        return sorted(self.policy_items, key=policy_item_key)

    def isUsingInheritedPolicy(self):
        """See IBranchVisibilityPolicy."""
        # If there is no inherited policy, we can never be using it.
        if self.inherited_policy is None:
            return False
        # If there are no explictly defined policy items, use the
        # inherited policy.
        return len(self.policy_items) == 0

    def setTeamPolicy(self, team, policy):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            product=self.product, project=self.project, team=team)
        if item is None:
            item = BranchVisibilityPolicyItem(
                product=self.product, project=self.project, team=team,
                policy=policy)
        else:
            item.policy = policy

    def removeTeam(self, team):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            product=self.product, project=self.project, team=team)
        if item is not None:
            BranchVisibilityPolicyItem.delete(item.id)
