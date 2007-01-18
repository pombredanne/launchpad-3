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

from canonical.database.sqlbase import SQLBase, sqlvalues, cursor
from canonical.launchpad.webapp.vocabulary import (
    NamedSQLObjectHugeVocabulary, IHugeVocabulary, BatchedCountableIterator)
from canonical.launchpad.interfaces import (
    IBinaryPackageName, IBinaryPackageNameSet, NotFoundError,
    IBinaryAndSourcePackageName)

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


class BinaryAndSourcePackageName(SQLBase):
    """See IBinaryAndSourcePackageName"""

    implements(IBinaryAndSourcePackageName)

    _table = 'BinaryAndSourcePackageNameView'
    _idName = 'name'
    _idType = str
    _defaultOrder = 'name'

    name = StringCol(dbName='name', notNull=True, unique=True,
                     alternateID=True)


class PackageNameIterator(BatchedCountableIterator):
    """Base class for package name vocabulary iteration.

    Includes convenience methods to build descriptions for source and
    binary packages based on guesswork using the binary package releases
    [loosely] associated to them.

    Note that the reason we use special iterators is to ensure that we
    only do the search for descriptions across source package names that
    we actually are attempting to list, taking advantage of the
    resultset slicing that BatchNavigator does.

    WARNING: the methods in this class assume that there is little
    overlap and much coherence in how package names are used, in
    particular across distributions if derivation is implemented. IOW,
    it does not make a promise to provide The Correct Description, but a
    pretty good guess at what the description should be.
    """
    MAX_TITLE_LENGTH = 50
    # XXX: this could live in a separate file to avoid needing to be
    # imported from sourcepackagename.py, but where?
    def getSourcePackageDescriptions(self, results, use_names=False):
        """Return a dictionary with descriptions keyed on source package names.

        Takes an ISelectResults of a *PackageName query. The use_names
        flag is a hack that allows this method to work for the
        BinaryAndSourcePackageName view, which lacks IDs.
        """
        # XXX: use_names could be removed if we instead added IDs to the
        # BinaryAndSourcePackageName view, but we'd still need to find
        # out how to specify the attribute, since it would be
        # sourcepackagename_id and binarypackagename_id depending on
        # whether the row represented one or both of those cases.
        #   -- kiko, 2007-01-17
        if use_names:
           clause = ("SourcePackageName.name in %s" %
                     sqlvalues([pn.name for pn in results]))
        else:
           clause = ("SourcePackageName.id in %s" %
                     sqlvalues([spn.id for spn in results]))

        cur = cursor()
        cur.execute("""SELECT DISTINCT BinaryPackageName.name,
                              SourcePackageName.name
                         FROM BinaryPackageRelease, SourcePackageName, Build,
                              SourcePackageRelease, BinaryPackageName
                        WHERE
                           BinaryPackageName.id = BinaryPackageRelease.id AND
                           BinaryPackageRelease.build = Build.ID AND
                           SourcePackageRelease.sourcepackagename =
                               SourcePackageName.id AND
                           Build.sourcepackagerelease =
                               SourcePackageRelease.id AND
                           %s
                       ORDER BY BinaryPackageName.name,
                                SourcePackageName.name"""
                        % clause)

        descriptions = {}
        for binarypackagename, sourcepackagename in cur.fetchall():
            if not descriptions.has_key(sourcepackagename):
                descriptions[sourcepackagename] = (
                    "Source of: %s" % binarypackagename)
            else:
                if len(descriptions[sourcepackagename]) > self.MAX_TITLE_LENGTH:
                    description = "..."
                else:
                    description = ", %s" % binarypackagename
                descriptions[sourcepackagename] += description
        return descriptions

    def getBinaryPackageDescriptions(self, results, use_names=False):
        """See getSourcePackageDescriptions, which is analogous to this."""
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
                if len(description) > self.MAX_TITLE_LENGTH:
                    description = (release.description[:self.MAX_TITLE_LENGTH]
                                  + "...")
                descriptions[binarypackagename] = description
        return descriptions


class BinaryAndSourcePackageNameIterator(PackageNameIterator):
    """Iterator for BinaryAndSourcePackageNameVocabulary.

    Builds descriptions from source and binary descriptions it can
    identify based on the names returned when queried.
    """
    def getTermsWithDescriptions(self, results):
        # Note that we grab first source package descriptions and then
        # binary package descriptions, giving preference to the latter,
        # via the update() call.
        descriptions = self.getSourcePackageDescriptions(results,
                                                         use_names=True)
        binary_descriptions = self.getBinaryPackageDescriptions(results,
                                                                use_names=True)
        descriptions.update(binary_descriptions)
        return [SimpleTerm(obj, obj.name,
                    descriptions.get(obj.name, "Not uploaded"))
                for obj in results]


class BinaryAndSourcePackageNameVocabulary(NamedSQLObjectHugeVocabulary):
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
    _orderBy = 'name'
    iterator = BinaryAndSourcePackageNameIterator


class BinaryPackageNameIterator(PackageNameIterator):
    """An iterator for BinaryPackageNameVocabulary.

    Builds descriptions based on releases of that binary package name.
    """
    def getTermsWithDescriptions(self, results):
        # Prefill the descriptions dictionary with the latest
        # description uploaded for that package name.
        descriptions = self.getBinaryPackageDescriptions(results)
        return [SimpleTerm(obj, obj.name,
                    descriptions.get(obj.name, "Not uploaded"))
                for obj in results]


class BinaryPackageNameVocabulary(NamedSQLObjectHugeVocabulary):
    """A vocabulary for searching for binary package names."""
    _table = BinaryPackageName
    _orderBy = 'name'
    displayname = 'Select a Binary Package'
    iterator = BinaryPackageNameIterator

