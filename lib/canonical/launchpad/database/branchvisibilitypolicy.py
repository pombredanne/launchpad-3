# Copyright 2007 Canonical Ltd.  All rights reserved.

"""BranchVisibilityPolicy interfaces."""

__metaclass__ = type

__all__ = [
    'BranchVisibilityPolicyItem',
    'DefaultPolicyItem',
    'BranchVisibilityPolicyList',
    ]

from zope.interface import implements

from sqlobject import ForeignKey

from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.lp.dbschema import BranchVisibilityPolicy

from canonical.launchpad.database import PillarName
from canonical.launchpad.interfaces import (
    IBranchVisibilityPolicyItem, IBranchVisibilityPolicy)


class BranchVisibilityPolicyItem(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityPolicyItem)
    _table = 'BranchVisibilityPolicy'
    # _defaultOrder = ['pillar', 'team.displayname']

    pillar = ForeignKey(dbName='pillar', foreignKey='PillarName', notNull=True)
    team = ForeignKey(dbName='team', foreignKey='Person', default=None)
    policy = EnumCol(schema=BranchVisibilityPolicy, notNull=True,
        default=BranchVisibilityPolicy.PUBLIC)


class DefaultPolicyItem:
    """A default policy item - one that isn't stored in the DB."""

    implements(IBranchVisibilityPolicyItem)

    team = None
    policy = BranchVisibilityPolicy.PUBLIC
        

def policy_item_key(item):
    if item.team is None:
        return None
    return item.team.displayname


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
            'BranchVisibilityPolicy.pillar = %s and '
            'BranchVisibilityPolicy.team is not NULL'
            % self.context_pillar.id
            )
        self.default_policy = BranchVisibilityPolicyItem.selectOneBy(
            pillar=self.context_pillar, team=None)
        if self.default_policy is None:
            self.default_policy = DefaultPolicyItem()

    @property
    def items(self):
        items = list(self.policy_items)
        items.append(self.default_policy)
        return sorted(items, key=policy_item_key)

    def setTeamPolicy(self, team, policy):
        """See IBranchVisibilityPolicy."""
        item = BranchVisibilityPolicyItem.selectOneBy(
            pillar=self.context_pillar, team=team)
        if item is None:
            item = BranchVisibilityPolicyItem(
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
            self._loadItems()

    def branchVisibilityTeamForUser(self, user):
        teams = []
        for item in self.policy_items:
            if (user.inTeam(item.team) and
                item.policy != BranchVisibilityPolicy.PUBLIC):
                teams.append(item.team)
        team_count = len(teams)
        if team_count == 1:
            return teams[0]
        elif team_count > 1:
            return user
        elif self.default_policy.policy == BranchVisibilityPolicy.PUBLIC:
            return None
        else:
            return user


