# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'SourcePackageName',
    'SourcePackageNameSet',
    'SourcePackageNameVocabulary'
]

from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

from sqlobject import SQLObjectNotFound
from sqlobject import StringCol, SQLMultipleJoin

from canonical.database.sqlbase import SQLBase, quote_like

from canonical.launchpad.webapp.vocabulary import (
    NamedSQLObjectHugeVocabulary)
from canonical.launchpad.interfaces import (
    ISourcePackageName, ISourcePackageNameSet, NotFoundError)

from canonical.launchpad.database.binarypackagename import (
    PackageNameIterator)


class SourcePackageName(SQLBase):
    implements(ISourcePackageName)
    _table = 'SourcePackageName'

    name = StringCol(dbName='name', notNull=True, unique=True,
        alternateID=True)

    potemplates = SQLMultipleJoin('POTemplate', joinColumn='sourcepackagename')
    packagings = SQLMultipleJoin('Packaging', joinColumn='sourcepackagename')
    
    def __unicode__(self):
        return self.name

    def ensure(klass, name):
        try:
            return klass.byName(name)
        except SQLObjectNotFound:
            return klass(name=name)
    ensure = classmethod(ensure)


class SourcePackageNameSet:
    implements(ISourcePackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def get(self, sourcepackagenameid):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        try:
            return SourcePackageName.get(sourcepackagenameid)
        except SQLObjectNotFound:
            raise NotFoundError(sourcepackagenameid)

    def getAll(self):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        return SourcePackageName.select()

    def findByName(self, name):
        """Find sourcepackagenames by its name or part of it."""
        query = "name ILIKE '%%' || %s || '%%'" % quote_like(name)
        return SourcePackageName.select(query)

    def queryByName(self, name):
        """See canonical.launchpad.interfaces.ISourcePackageNameSet."""
        return SourcePackageName.selectOneBy(name=name)

    def new(self, name):
        return SourcePackageName(name=name)

    def getOrCreateByName(self, name):
        try:
            return self[name]
        except NotFoundError:
            return self.new(name)


class SourcePackageNameIterator(PackageNameIterator):
    """A custom iterator for SourcePackageNameVocabulary.

    Used to iterate over vocabulary items and provide full
    descriptions.
    """
    def getTermsWithDescriptions(self, results):
        descriptions = self.getSourcePackageDescriptions(results)
        return [SimpleTerm(obj, obj.name,
                    descriptions.get(obj.name, "Not yet built"))
                for obj in results]


class SourcePackageNameVocabulary(NamedSQLObjectHugeVocabulary):
    """A vocabulary that lists source package names."""
    displayname = 'Select a Source Package'
    _table = SourcePackageName
    _orderBy = 'name'
    iterator = SourcePackageNameIterator

