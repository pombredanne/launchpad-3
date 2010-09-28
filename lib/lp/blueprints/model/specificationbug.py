# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type

__all__ = ['SpecificationBug']

from sqlobject import ForeignKey
from zope.interface import implements

from canonical.database.sqlbase import SQLBase
from lp.blueprints.interfaces.specificationbug import ISpecificationBug


class SpecificationBug(SQLBase):
    """A link between a spec and a bug."""

    implements(ISpecificationBug)

    _table = 'SpecificationBug'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug',
        notNull=True)

    @property
    def target(self):
        """See IBugLink."""
        return self.specification

