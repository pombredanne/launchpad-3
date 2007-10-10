# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'Component',
    'ComponentSelection',
    'ComponentSet'
    ]

from zope.interface import implements

from sqlobject import StringCol, ForeignKey

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IComponent, IComponentSelection, IComponentSet, NotFoundError)


class Component(SQLBase):
    """See IComponent."""

    implements(IComponent)

    _defaultOrder= ['id']

    name = StringCol(notNull=True, alternateID=True)


class ComponentSelection(SQLBase):
    """See IComponentSelection."""

    implements(IComponentSelection)

    _defaultOrder= ['id']

    distroseries = ForeignKey(dbName='distrorelease',
                               foreignKey='DistroSeries', notNull=True)
    component = ForeignKey(dbName='component',
                           foreignKey='Component', notNull=True)


class ComponentSet:
    """See IComponentSet."""

    implements(IComponentSet)

    def __iter__(self):
        """See IComponentSet."""
        return iter(Component.select())

    def __getitem__(self, name):
        """See IComponentSet."""
        component = Component.selectOneBy(name=name)
        if component is not None:
            return component
        raise NotFoundError(name)

    def get(self, component_id):
        """See IComponentSet."""
        return Component.get(component_id)

    def ensure(self, name):
        """See IComponentSet."""
        component = Component.selectOneBy(name=name)
        if component is not None:
            return component
        return self.new(name)


    def new(self, name):
        """See IComponentSet."""
        return Component(name=name)

