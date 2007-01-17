# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'BinaryPackageName', 
    'BinaryPackageNameSet',
    'BinaryAndSourcePackageName',
    'BinaryAndSourcePackageNameVocabulary',
    'BinaryPackageNameVocabulary'
]

# Zope imports
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

# SQLObject/SQLBase
from sqlobject import (
    SQLObjectNotFound, StringCol, SQLMultipleJoin, CONTAINSSTRING)

from canonical.database.sqlbase import SQLBase, quote_like
from canonical.launchpad.webapp.vocabulary import (
    NamedSQLObjectHugeVocabulary, SQLObjectVocabularyBase, IHugeVocabulary)
from canonical.launchpad.interfaces import (
    IBinaryPackageName, IBinaryPackageNameSet, NotFoundError,
    IBinaryAndSourcePackageName)


class BinaryPackageName(SQLBase):

    implements(IBinaryPackageName)
    _table = 'BinaryPackageName'
    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)

    binarypackages = SQLMultipleJoin(
        'BinaryPackage', joinColumn='binarypackagename'
        )

    def __unicode__(self):
        return self.name


class BinaryPackageNameSet:
    implements(IBinaryPackageNameSet)

    def __getitem__(self, name):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            raise NotFoundError(name)

    def getAll(self):
        """See canonical.launchpad.interfaces.IBinaryPackageNameSet."""
        return BinaryPackageName.select()

    def findByName(self, name):
        """Find binarypackagenames by its name or part of it."""
        return BinaryPackageName.select(
            CONTAINSSTRING(BinaryPackageName.q.name, name))

    def queryByName(self, name):
        return BinaryPackageName.selectOneBy(name=name)

    def new(self, name):
        return BinaryPackageName(name=name)

    def getOrCreateByName(self, name):
        try:
            return self[name]
        except NotFoundError:
            return self.new(name)

    def ensure(self, name):
        """Ensure that the given BinaryPackageName exists, creating it
        if necessary.

        Returns the BinaryPackageName
        """
        try:
            return BinaryPackageName.byName(name)
        except SQLObjectNotFound:
            return BinaryPackageName(name=name)


class BinaryAndSourcePackageName(SQLBase):
    """See IBinaryAndSourcePackageName"""

    implements(IBinaryAndSourcePackageName)

    _table = 'BinaryAndSourcePackageNameView'
    _idName = 'name'
    _idType = str
    _defaultOrder = 'name'

    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)


class BinaryAndSourcePackageNameVocabulary(SQLObjectVocabularyBase):
    """A vocabulary for searching for binary and sourcepackage names.

    This is useful for, e.g., reporting a bug on a 'package' when a reporter
    often has no idea about whether they mean a 'binary package' or a 'source
    package'.

    The value returned by a widget using this vocabulary will be either an
    ISourcePackageName or an IBinaryPackageName.
    """
    implements(IHugeVocabulary)

    _table = BinaryAndSourcePackageName
    displayname = 'Select a Package'

    def __contains__(self, name):
        return self._table.selectOneBy(name=name)

    def getTermByToken(self, token):
        name = self._table.selectOneBy(name=token)
        if name is None:
            raise LookupError(token)
        return self.toTerm(name)

    def search(self, query):
        """Find matching source and binary package names."""
        if not query:
            return self.emptySelectResults()

        query = "name ILIKE '%%' || %s || '%%'" % quote_like(query)
        return self._table.select(query)

    def toTerm(self, obj):
        return SimpleTerm(obj.name, obj.name, obj.name)


class BinaryPackageNameVocabulary(NamedSQLObjectHugeVocabulary):

    _table = BinaryPackageName
    _orderBy = 'name'
    displayname = 'Select a Binary Package'

    def toTerm(self, obj):
        return SimpleTerm(obj, obj.name, obj.name)

    def search(self, query):
        """Return IBinaryPackageNames matching the query.

        Returns an empty list if query is None or an empty string.
        """
        if not query:
            return self.emptySelectResults()

        query = query.lower()
        return self._table.select(
            "BinaryPackageName.name LIKE '%%' || %s || '%%'"
            % quote_like(query))

