# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['POTemplateNameSet', 'POTemplateName']

from zope.interface import implements

from sqlobject import (
    StringCol, SQLMultipleJoin, SQLObjectNotFound, OR, CONTAINSSTRING)
from canonical.database.sqlbase import SQLBase

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IPOTemplateName, IPOTemplateNameSet, NotFoundError)


class POTemplateNameSet:
    implements(IPOTemplateNameSet)

    def __getitem__(self, name):
        """See IPOTemplateNameSet."""
        try:
            return POTemplateName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError, name

    def __iter__(self):
        """See IPOTemplateNameSet."""
        for potemplatename in POTemplateName.select():
            yield potemplatename

    def get(self, potemplatenameid):
        """See IPOTemplateNameSet."""
        try:
            return POTemplateName.get(potemplatenameid)
        except SQLObjectNotFound:
            raise NotFoundError, potemplatenameid

    def new(self, translationdomain, title, name=None, description=None):
        """See IPOTemplateNameSet."""
        if name is None:
            name = helpers.getValidNameFromString(translationdomain)
        return POTemplateName(name=name, title=title, description=description,
                              translationdomain=translationdomain)

    def _search(self, text):
        """Return an SQLObject ResultSet with all POTemplateName that matches.

        The search is done in name, title, description and translationdomain
        fields based on the 'text' input.
        """
        if text:
            text.lower()
            results = POTemplateName.select(
                OR (
                    CONTAINSSTRING(POTemplateName.q.name, text),
                    CONTAINSSTRING(POTemplateName.q.title, text),
                    CONTAINSSTRING(POTemplateName.q.description, text),
                    CONTAINSSTRING(POTemplateName.q.translationdomain, text)
                    ),
                orderBy='name'
                )
        else:
            results = None

        return results

    def search(self, text):
        """See IPOTemplateNameSet."""
        results = self._search(text)

        for potemplatename in results:
            yield potemplatename

    def searchCount(self, text):
        """See IPOTemplateNameSet."""
        results = self._search(text)

        if results is not None:
            return results.count()
        else:
            return 0


class POTemplateName(SQLBase):
    implements(IPOTemplateName)

    _table = 'POTemplateName'

    name = StringCol(dbName='name', notNull=True, unique=True, alternateID=True)
    title = StringCol(dbName='title', notNull=True)
    description = StringCol(dbName='description', notNull=False, default=None)
    translationdomain = StringCol(dbName='translationdomain', notNull=True,
        unique=True, alternateID=True)
    potemplates = SQLMultipleJoin('POTemplate', joinColumn='potemplatename')

