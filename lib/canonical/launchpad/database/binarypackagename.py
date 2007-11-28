# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'BinaryPackageName',
    'BinaryPackageNameSet',
    'BinaryPackageNameVocabulary',
    'getBinaryPackageDescriptions'
]

# Zope imports
from zope.interface import implements
from zope.schema.vocabulary import SimpleTerm

# SQLObject/SQLBase
from sqlobject import (
    SQLObjectNotFound, StringCol, SQLMultipleJoin, CONTAINSSTRING)

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.webapp.vocabulary import (
    NamedSQLObjectHugeVocabulary, BatchedCountableIterator)
from canonical.launchpad.interfaces import (
    IBinaryPackageName, IBinaryPackageNameSet, NotFoundError)
from canonical.launchpad.database.binarypackagerelease import (
    BinaryPackageRelease)


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


class BinaryPackageNameIterator(BatchedCountableIterator):
    """An iterator for BinaryPackageNameVocabulary.

    Builds descriptions based on releases of that binary package name.
    """
    def getTermsWithDescriptions(self, results):
        # Prefill the descriptions dictionary with the latest
        # description uploaded for that package name.
        descriptions = getBinaryPackageDescriptions(results)
        return [SimpleTerm(obj, obj.name,
                    descriptions.get(obj.name, "Not uploaded"))
                for obj in results]


class BinaryPackageNameVocabulary(NamedSQLObjectHugeVocabulary):
    """A vocabulary for searching for binary package names."""
    _table = BinaryPackageName
    _orderBy = 'name'
    displayname = 'Select a Binary Package'
    iterator = BinaryPackageNameIterator


def getBinaryPackageDescriptions(results, use_names=False, max_title_length=50):
    """Return a dict of descriptions keyed by package name.

    See sourcepackage.py:getSourcePackageDescriptions, which is analogous.
    """
    if use_names:
       clause = ("BinaryPackageName.name in %s" %
                 sqlvalues([pn.name for pn in results]))
    else:
       clause = ("BinaryPackageName.id in %s" %
                 sqlvalues([bpn.id for bpn in results]))

    descriptions = {}
    releases = BinaryPackageRelease.select(
        """BinaryPackageRelease.binarypackagename =
            BinaryPackageName.id AND
           %s""" % clause,
        clauseTables=["BinaryPackageRelease", "BinaryPackageName"],
        orderBy=["-BinaryPackageRelease.datecreated"])

    for release in releases:
        binarypackagename = release.binarypackagename.name
        if not descriptions.has_key(binarypackagename):
            description = release.description.strip().replace("\n", " ")
            if len(description) > max_title_length:
                description = (release.description[:max_title_length]
                              + "...")
            descriptions[binarypackagename] = description
    return descriptions

