# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'Component',
    'ComponentSelection',
    'ComponentSet'
    ]

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from zope.interface import implementer

from lp.app.errors import NotFoundError
from lp.services.database.sqlbase import SQLBase
from lp.soyuz.interfaces.component import (
    IComponent,
    IComponentSelection,
    IComponentSet,
    )


@implementer(IComponent)
class Component(SQLBase):
    """See IComponent."""

    _defaultOrder = ['id']

    name = StringCol(notNull=True, alternateID=True)

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)


@implementer(IComponentSelection)
class ComponentSelection(SQLBase):
    """See IComponentSelection."""

    _defaultOrder = ['id']

    distroseries = ForeignKey(dbName='distroseries',
                               foreignKey='DistroSeries', notNull=True)
    component = ForeignKey(dbName='component',
                           foreignKey='Component', notNull=True)


@implementer(IComponentSet)
class ComponentSet:
    """See IComponentSet."""

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
