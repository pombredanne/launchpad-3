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

from canonical.launchpad.helpers import shortlist
from canonical.launchpad.database import PillarName
from canonical.launchpad.interfaces import (
    IBranchVisibilityPolicyItem, IBranchVisibilityPolicy)


class BranchVisibilityPolicyItem(SQLBase):
    """A sequence of ordered revisions in Bazaar."""

    implements(IBranchVisibilityPolicyItem)
    _table = 'BranchVisibilityPolicy'
    # The policy item is explicitly defined in the database.
    _implicit = False

    pillar = ForeignKey(dbName='pillar', foreignKey='PillarName', notNull=True)
    team = ForeignKey(dbName='team', foreignKey='Person', default=None)
    policy = EnumCol(schema=BranchVisibilityPolicy, notNull=True,
        default=BranchVisibilityPolicy.PUBLIC)


class DefaultPolicyItem:
    """A default policy item - one that isn't stored in the DB."""

    implements(IBranchVisibilityPolicyItem)
    # The policy item is the implicit public policy.
    _implicit = True

    team = None
    policy = BranchVisibilityPolicy.PUBLIC
        

def policy_item_key(item):
    if item.team is None:
        return None
    return item.team.displayname


class BranchVisibilityPolicyList:
    """Specifies a list of branch visibility policy items."""

    implements(IBranchVisibilityPolicy)

    def __init__(self, context, inherited_policy=None):
        self.context = context
        self.inherited_policy = inherited_policy
        self.context_pillar = PillarName.selectOneBy(name=context.name)
        self._loadItems()

    def _loadItems(self):
        # The query is listified here to get something we can
        # actually query the length of.
        self.policy_items = shortlist(BranchVisibilityPolicyItem.select(
            'BranchVisibilityPolicy.pillar = %s and '
            'BranchVisibilityPolicy.team is not NULL'
            % self.context_pillar.id
            ))
        self.default_policy = BranchVisibilityPolicyItem.selectOneBy(
            pillar=self.context_pillar, team=None)
        if self.default_policy is None:
            self.default_policy = DefaultPolicyItem()

    @property
    def items(self):
        # If we are using the inherited policy return the items
        # from the inherited context.
        if self.isUsingInheritedPolicy():
            return self.inherited_policy.items
        # Copy the policy_items list, don't just get a reference to it.
        items = list(self.policy_items)
        items.append(self.default_policy)
        return sorted(items, key=policy_item_key)

    def isUsingInheritedPolicy(self):
        """See IBranchVisibilityPolicy."""
        # If there is no inherited policy, we can never be using it.
        if self.inherited_policy is None:
            return False
        # If there are no explictly defined policy items, use the
        # inherited policy.
        if len(self.policy_items) == 0 and self.default_policy._implicit:
            return True
        else:
            return False

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
        """See IBranchVisibilityPolicy."""
        teams = []
        items = self.items
        # We know that the first item is the policy for everyone.
        default_policy = items[0]
        team_policies = items[1:]
        for item in team_policies:
            if (user.inTeam(item.team) and
                item.policy != BranchVisibilityPolicy.PUBLIC):
                teams.append(item.team)
        team_count = len(teams)
        if team_count == 1:
            return teams[0]
        elif team_count > 1:
            return user
        elif default_policy.policy == BranchVisibilityPolicy.PUBLIC:
            return None
        else:
            return user


