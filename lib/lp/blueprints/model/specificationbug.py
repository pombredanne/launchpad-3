# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = ['SpecificationBug']

from lazr.restful.interfaces import IJSONPublishable
from sqlobject import ForeignKey
from zope.interface import implementer

from lp.blueprints.interfaces.specificationbug import ISpecificationBug
from lp.services.database.sqlbase import SQLBase


@implementer(ISpecificationBug, IJSONPublishable)
class SpecificationBug(SQLBase):
    """A link between a spec and a bug."""

    _table = 'SpecificationBug'
    specification = ForeignKey(dbName='specification',
        foreignKey='Specification', notNull=True)
    bug = ForeignKey(dbName='bug', foreignKey='Bug',
        notNull=True)

    @property
    def target(self):
        """See IBugLink."""
        return self.specification

    def toDataForJSON(self, media_type):
        """See IJSONPublishable.

        These objects have no JSON representation.
        """
        return None
