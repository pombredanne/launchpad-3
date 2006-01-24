# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'Section',
    'SectionSet'
    ]

from zope.interface import implements

from sqlobject import (
    StringCol, SQLObjectNotFound)

from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    NotFoundError, ISection, ISectionSet)


class Section(SQLBase):
    """Section table SQLObject."""
    implements(ISection)

    name = StringCol(notNull=True, alternateID=True)


class SectionSet:
    """Set manipulation tools for Section table."""
    implements(ISectionSet)

    def __iter__(self):
        """See ISectionSet."""
        return iter(Section.select())

    def __getitem__(self, name):
        """See ISectionSet."""
        section = Section.selectOneBy(name=name)
        if section:
            return section
        raise NotFoundError(name)

    def get(self, section_id):
        """See ISectionSet."""
        return Section.get(section_id)

    def ensure(self, name):
        """See ISectionSet."""
        section = Section.selectOneBy(name=name)
        if section:
            return section
        return self.new(name)

    def new(self, name):
        """See ISectionSet."""
        return Section(name=name)

