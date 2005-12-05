# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Component',
    'ComponentSet'
           ]

from zope.interface import implements

from sqlobject import (
    StringCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IComponent, IComponentSet, NotFoundError)


class Component(SQLBase):
    """Component table SQLObject """
    implements(IComponent)

    name = StringCol(notNull=True, alternateID=True)


class ComponentSet:
    """Set manipulation tools for Component table."""
    implements(IComponentSet)

    def __iter__(self):
        """See IComponentSet."""
        return iter(Component.select())

    def __getitem__(self, name):
        """See IComponentSet."""
        try:
            return Component.selectOneBy(name=name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def get(self, component_id):
        """See IComponentSet."""
        return Component.get(component_id)

    def new(self, name):
        """See IComponentSet."""
        return Component(name=name)
        
