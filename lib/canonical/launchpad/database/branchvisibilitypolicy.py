# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityPolicyList',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad.database import PillarNameSet
from canonical.launchpad.interfaces import (
    IBranchVisibilityPolicyItem, IBranchVisibilityPolicy)


class BranchVisibilityPolicyItem(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityPolicyItem)
    _table = 'BranchVisibilityPolicy'
    _defaultOrder = ['pillar', 'team.displayname']

    pillar = ForeignKey(dbName='pillar', foreignKey='PillarName', notNull=True)
    team = ForeignKey(dbName='team', foreignKey='Person', default=None)
    policy = EnumCol(schema=BranchVisibilityPolicy, notNull=True,
        default=BranchVisibilityPolicy.PUBLIC)


class BranchVisibilityPolicyList:
    """Specifies a list of branch visibility policy items."""

    implements(IBranchVisibilityPolicy)

    def __init__(self, context):
        self.context = context
        self.context_pillar = PillarName.selectOneBy(name=context.name)
        self._loadItems()

    def _loadItems(self):
        # load items for context
        self.policy_items = BranchVisibilityPolicyItem.select(
            'BranchVisibilityPolicy.pillar = %s'
            % self.context_pillar.id
            )

    @property
    def items(self):
        return self.policy_items

    def setTeamPolicy(self, team, policy):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            pillar=self.context_pillar, team=team)
        if item is None:
            item = BranchVisibilityPolicyItem.new(
                pillar=self.context_pillar, team=team, policy=policy)
            self._loadItems()
        else:
            item.policy = policy
        
    def removeTeam(self, team):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            pillar=self.context_pillar, team=team)
        if item is not None:
            BranchVisibilityPolicyItem.delete(item.id)
        
